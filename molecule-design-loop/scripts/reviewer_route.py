#!/usr/bin/env python3
"""Pick the reviewer and search backends for a run, without calling any model.

Why this exists
---------------
Steps 3.5, 9.5 and 11 need an independent reviewer, and Steps 1.5-B and 5.5 need a
literature search. Both used to be wired to one provider. When that provider was
unreachable (no credits, no licence, a region block, a CLI that would not start),
the mandatory steps had no way forward except an ad-hoc switch that nobody recorded.

This script makes the choice explicit and repeatable:

  selection order   this invocation > project file > user file > default (gemini)
  project file      molecule-design-stage/reviewer.json
  user file         $XDG_CONFIG_HOME/molecule-design-loop/reviewer.json
                    (default ~/.config/molecule-design-loop/reviewer.json)

  {"review": {"backend": "codex", "model": null, "effort": "high"},
   "search": {"backend": "gemini"},
   "fallback": ["codex@agent-hud", "deepseek@agent-hud", "manual"]}

A flat {"backend": ..., "via": ..., "model": ..., "effort": ..., "fallback": [...]}
applies to both roles. `fallback` is opt-in: with none, an unavailable backend stops
the step.

Two transports reach a backend:
  direct     its own MCP bridge (gemini-review / gemini-research, codex, antigravity,
             claude-review), or a native sub-agent when the host is Codex;
  agent-hud  a separate agent session opened through the Agent HUD MCP
             (start_session / send_message / get_message). Write "codex@agent-hud"
             or {"backend": "codex", "via": "agent-hud"}. DeepSeek is reachable only
             this way. The session is a whole agent the executor can talk to, which
             is what the review rebuttal exchange uses.

It never launches a review and never edits settings. It answers three questions:

  resolve       which backend, transport, model and tools to use for a role, given
                the tools the host exposes (--available) and backends that already
                failed (--failed backend[@agent-hud]:reason). A switch to the next
                fallback happens only for failures that prove the request never ran
                (tool missing, start failure, auth / billing / region / model rejected,
                refused before delivery). A timeout or a dropped connection may have
                run -- and billed -- a review, so it stops with status "unavailable".
  independence  whether the reviewer's model is a different family from the
                executor's. A same-family review is provisional, never accepted.
  show          both roles at once, plus which config files were found -- the
                check to run after setting up a machine.
  backends      the backend table, for humans.

Exit codes: 0 resolved, 2 configuration error, 3 no usable backend (REVIEW_UNAVAILABLE).
"""
import argparse
import json
import os
import re
import sys

ROLES = ("review", "search")
HOSTS = ("claude-code", "codex")
VIAS = ("direct", "agent-hud")
DEFAULT_BACKEND = "gemini"
ALIASES = {"claude": "claude-code", "claude-review": "claude-code", "agy": "antigravity"}

# search: "yes" = the transport searches; "needs_check" = only if that session has web
# search, so a reply without retrieved sources is incomplete; "no" = cannot serve search.
# hud_client: the Agent HUD client name, or None when Agent HUD cannot open it.
BACKENDS = {
    "gemini": {
        "family": "google",
        "default_model": "gemini-2.5-flash",
        "search": "yes",
        "hud_client": None,
        "tools": {
            "review": {
                "fresh": "mcp__gemini-review__review",
                "continue": "mcp__gemini-review__review_reply",
                "async_start": "mcp__gemini-review__review_start",
                "async_status": "mcp__gemini-review__review_status",
            },
            "search": {
                "fresh": "mcp__gemini-research__prior_art_search_start",
                "literature": "mcp__gemini-research__literature_search_start",
                "async_status": "mcp__gemini-research__literature_search_status",
            },
        },
    },
    "codex": {
        "family": "openai",
        "default_model": None,
        "search": "needs_check",
        "hud_client": "codex",
        "tools": {
            role: {"fresh": "mcp__codex__codex", "continue": "mcp__codex__codex-reply"}
            for role in ROLES
        },
    },
    "antigravity": {
        "family": "google",
        "default_model": None,
        "search": "needs_check",
        "hud_client": "antigravity",
        "tools": {
            role: {
                "fresh": "mcp__antigravity__antigravity",
                "continue": "mcp__antigravity__antigravity-reply",
            }
            for role in ROLES
        },
    },
    "claude-code": {
        "family": "anthropic",
        "default_model": None,
        "search": "no",
        "hud_client": "claude",
        "tools": {
            role: {
                "fresh": "mcp__claude-review__review",
                "continue": "mcp__claude-review__review_reply",
                "async_start": "mcp__claude-review__review_start",
                "async_status": "mcp__claude-review__review_status",
            }
            for role in ROLES
        },
    },
    "deepseek": {
        "family": "deepseek",
        "default_model": None,
        "search": "needs_check",
        "hud_client": "deepseek",
        "tools": None,  # no direct bridge: Agent HUD only
    },
    "manual": {
        "family": "unknown",
        "default_model": None,
        "search": "needs_check",
        "hud_client": None,
        "tools": {role: {} for role in ROLES},
    },
}

HUD_TOOLS = {
    "fresh": "mcp__agent-hud__start_session",
    "continue": "mcp__agent-hud__send_message",
    "async_status": "mcp__agent-hud__get_message",
}
# Inside Codex the codex backend is a fresh native sub-agent, not the MCP bridge.
CODEX_NATIVE_TOOLS = {"fresh": "spawn_agent", "continue": "send_input"}
HOST_FAMILY = {"claude-code": "anthropic", "codex": "openai"}

# Failures that prove no review ran, so trying the next fallback cannot double-run one.
SWITCHABLE = {
    "tool_missing", "start_failed", "auth_rejected", "billing_rejected",
    "region_unavailable", "model_unsupported", "refused",
}
# Failures after dispatch: the review may have run. Stop; never switch provider.
# pass_limit is Agent HUD's back-and-forth limit: only the user can lift it.
NOT_SWITCHABLE = {
    "timeout", "disconnected", "server_error", "parse_error", "rate_limited",
    "cancelled", "empty_reply", "expired", "uncertain", "pass_limit",
}

FAMILY_PATTERNS = [
    (r"claude|opus|sonnet|haiku|fable", "anthropic"),
    (r"gpt|codex|^o\d", "openai"),
    (r"gemini|gemma", "google"),
    (r"grok", "xai"),
    (r"deepseek", "deepseek"),
    (r"qwen", "alibaba"),
    (r"llama", "meta"),
    (r"mistral|mixtral", "mistral"),
]


class ConfigError(ValueError):
    pass


def model_family(model):
    """Family from a model id, or 'unknown'. Bridge names are not evidence."""
    if not model:
        return "unknown"
    name = str(model).strip().lower().split("/")[-1]
    for pattern, family in FAMILY_PATTERNS:
        if re.search(pattern, name):
            return family
    return "unknown"


def parse_backend(value, via=None):
    """'codex', 'codex@agent-hud' or ('codex', via='agent-hud') -> (backend, via)."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("backend must be a nonempty string")
    text = value.strip().lower()
    if "@" in text:
        text, suffix = text.split("@", 1)
        if via is not None and via != suffix:
            raise ConfigError(f"{value!r} conflicts with via={via!r}")
        via = suffix
    name = ALIASES.get(text, text)
    if name not in BACKENDS:
        raise ConfigError(f"unknown backend {value!r}; choose from {', '.join(sorted(BACKENDS))}")
    if via is None:
        via = "agent-hud" if BACKENDS[name]["tools"] is None else "direct"
    if via not in VIAS:
        raise ConfigError(f"unknown transport {via!r}; choose from {', '.join(VIAS)}")
    if via == "agent-hud" and not BACKENDS[name]["hud_client"]:
        raise ConfigError(f"{name} cannot be opened through Agent HUD")
    if via == "direct" and BACKENDS[name]["tools"] is None:
        raise ConfigError(f"{name} has no direct bridge; use {name}@agent-hud")
    return name, via


def label(entry):
    backend, via = entry
    return backend if via == "direct" else f"{backend}@{via}"


def user_config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "molecule-design-loop", "reviewer.json")


FIELDS = {"backend", "via", "model", "effort", "fallback"}


def load_config(path):
    """Return {role: {...}} from one file, or {} when the file does not exist."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as err:
        raise ConfigError(f"cannot read {path}: {err}") from err
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must hold a JSON object")
    unknown = set(data) - FIELDS - set(ROLES)
    if unknown:
        raise ConfigError(f"unknown fields in {path}: {', '.join(sorted(unknown))}")
    shared = {k: data[k] for k in FIELDS if k in data}
    layer = {}
    for role in ROLES:
        block = data.get(role, {})
        if not isinstance(block, dict):
            raise ConfigError(f"{path}: '{role}' must be an object")
        extra = set(block) - FIELDS
        if extra:
            raise ConfigError(f"unknown fields in {path} '{role}': {', '.join(sorted(extra))}")
        merged = {**shared, **block}
        if merged:
            layer[role] = normalise(merged, f"{path} '{role}'")
    return layer


def normalise(block, where):
    out = {}
    if block.get("backend") is not None:
        out["backend"] = parse_backend(block["backend"], block.get("via"))
    elif block.get("via") is not None:
        raise ConfigError(f"{where}: 'via' needs a 'backend'")
    for field in ("model", "effort"):
        value = block.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ConfigError(f"{where}: {field} must be a nonempty string or null")
        if value is not None:
            out[field] = value.strip()
    if block.get("fallback") is not None:
        chain = block["fallback"]
        if isinstance(chain, str):
            chain = [c for c in chain.split(",") if c.strip()]
        if not isinstance(chain, list):
            raise ConfigError(f"{where}: fallback must be a list of backends")
        out["fallback"] = [parse_backend(c) for c in chain]
    return out


def pick(layers, role):
    """Apply invocation > project > user > default for one role."""
    backend, source = parse_backend(DEFAULT_BACKEND), "default"
    for name, layer in layers:
        block = layer.get(role, {})
        if "backend" in block:
            backend, source = block["backend"], name
            break
    chosen = {"backend": backend, "source": source}
    for field in ("model", "effort", "fallback"):
        for _, layer in layers:
            block = layer.get(role, {})
            if field not in block:
                continue
            # A layer naming another backend does not lend it its model or effort;
            # a layer naming no backend (an inline --model) applies to the chosen one.
            if field != "fallback" and block.get("backend", backend)[0] != backend[0]:
                continue
            chosen[field] = block[field]
            break
    return chosen


def norm_tool(name):
    return re.sub(r"[-.]", "_", name.lower())


def tools_for(entry, role, host):
    backend, via = entry
    if via == "agent-hud":
        return {**HUD_TOOLS, "client": BACKENDS[backend]["hud_client"]}
    if backend == "codex" and host == "codex":
        return dict(CODEX_NATIVE_TOOLS)
    return dict(BACKENDS[backend]["tools"][role])


def transport_of(entry, host):
    backend, via = entry
    if via == "agent-hud":
        return "agent-hud"
    if backend == "manual":
        return "manual"
    return "native" if backend == "codex" and host == "codex" else "mcp"


def parse_failed(entries):
    failed = {}
    for item in entries or []:
        if ":" not in item:
            raise ConfigError(f"--failed takes backend:reason, got {item!r}")
        backend, reason = item.rsplit(":", 1)
        reason = reason.strip()
        if reason not in SWITCHABLE | NOT_SWITCHABLE:
            raise ConfigError(
                f"unknown failure reason {reason!r}; one of "
                f"{', '.join(sorted(SWITCHABLE | NOT_SWITCHABLE))}"
            )
        failed[parse_backend(backend)] = reason
    return failed


def resolve(role, host, project_file=None, user_file=None, inline=None, available=None,
            failed=None, executor_model=None, allow_same_family=False):
    if role not in ROLES:
        raise ConfigError(f"unknown role {role!r}")
    if host not in HOSTS:
        raise ConfigError(f"unknown host {host!r}")
    inline_layer = {role: normalise(inline, "invocation")} if inline else {}
    layers = [("invocation", inline_layer), ("project", load_config(project_file)),
              ("user", load_config(user_file))]
    chosen = pick(layers, role)
    primary = chosen["backend"]
    chain = [primary] + [e for e in chosen.get("fallback", []) if e != primary]
    executor_family = model_family(executor_model) if executor_model else HOST_FAMILY[host]
    available_set = None if available is None else {norm_tool(t) for t in available}
    failed = failed or {}

    skipped = []
    for position, entry in enumerate(chain):
        backend = entry[0]
        spec = BACKENDS[backend]
        model = (chosen.get("model") if position == 0 else None) or spec["default_model"]
        family = model_family(model) if model else spec["family"]
        reason = None
        if role == "search" and spec["search"] == "no":
            reason = "cannot_search"
        elif family != "unknown" and family == executor_family and not allow_same_family:
            reason = "same_family_as_executor"
        elif entry in failed:
            if failed[entry] in NOT_SWITCHABLE:
                return unavailable(role, host, chain, skipped + [
                    {"backend": label(entry), "reason": failed[entry]}],
                    f"{label(entry)} failed after dispatch ({failed[entry]}); the review may "
                    "have run, so no other provider is tried. Check the raw output, then "
                    "ask the user.")
            reason = failed[entry]
        elif available_set is not None and transport_of(entry, host) != "manual":
            needed = tools_for(entry, role, host)["fresh"]
            if norm_tool(needed) not in available_set:
                reason = "tool_missing"
        if reason:
            if position == 0 and reason in ("cannot_search", "same_family_as_executor") \
                    and chosen["source"] != "default":
                raise ConfigError(
                    f"{label(entry)} was selected for {role} by the {chosen['source']} but "
                    + ("cannot search the literature" if reason == "cannot_search" else
                       f"is the executor's own family ({executor_family}); pass "
                       "--allow-same-family only for a run whose reviews stay provisional")
                )
            skipped.append({"backend": label(entry), "reason": reason})
            continue
        return {
            "status": "ok",
            "role": role,
            "host": host,
            "backend": backend,
            "via": entry[1],
            "label": label(entry),
            "source": chosen["source"] if position == 0 else "fallback",
            "model": model,
            "effort": chosen.get("effort") if position == 0 else None,
            "transport": transport_of(entry, host),
            "tools": tools_for(entry, role, host),
            "search_capability": spec["search"],
            "expected_family": family,
            "executor_family": executor_family,
            "same_family_allowed": bool(allow_same_family and family == executor_family),
            "chain": [label(e) for e in chain],
            "skipped": skipped,
        }
    return unavailable(role, host, chain, skipped,
                       "no backend in the chain is usable; the step stops (REVIEW_UNAVAILABLE)")


def unavailable(role, host, chain, skipped, message):
    return {"status": "unavailable", "role": role, "host": host,
            "chain": [label(e) for e in chain], "skipped": skipped, "message": message}


def independence(executor_model, reviewer_model):
    executor, reviewer = model_family(executor_model), model_family(reviewer_model)
    if "unknown" in (executor, reviewer):
        verdict = "unknown"
    elif executor == reviewer:
        verdict = "same_family"
    else:
        verdict = "independent"
    return {"executor_model": executor_model, "executor_family": executor,
            "reviewer_model": reviewer_model, "reviewer_family": reviewer,
            "verdict": verdict, "accepted": verdict == "independent"}


def show_setup(args):
    project = os.path.join(args.stage_dir, "reviewer.json")
    user = args.user_config or user_config_path()
    available = None if args.available is None else \
        [t.strip() for t in args.available.split(",") if t.strip()]
    report = {
        "config_files": {
            "project": {"path": project, "found": os.path.exists(project)},
            "user": {"path": user, "found": os.path.exists(user)},
        },
        "routes": {},
    }
    for role in ROLES:
        try:
            report["routes"][role] = resolve(role, args.host, project_file=project,
                                             user_file=user, available=available,
                                             executor_model=args.executor_model)
        except ConfigError as err:
            report["routes"][role] = {"status": "config_error", "message": str(err)}
    if available is None:
        report["note"] = ("tools not checked: pass --available with the mcp__ tool names "
                          "this host exposes to see which backends are actually reachable")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    res = sub.add_parser("resolve", help="pick the backend for one role")
    res.add_argument("--role", choices=ROLES, required=True)
    res.add_argument("--host", choices=HOSTS, required=True)
    res.add_argument("--stage-dir", default="molecule-design-stage",
                     help="folder holding reviewer.json (default: molecule-design-stage)")
    res.add_argument("--user-config", default=None,
                     help="user-level config (default: $XDG_CONFIG_HOME or ~/.config "
                          "/molecule-design-loop/reviewer.json)")
    res.add_argument("--no-user-config", action="store_true")
    res.add_argument("--backend", help="this invocation's choice, e.g. codex or "
                     "deepseek@agent-hud (overrides the files)")
    res.add_argument("--via", choices=VIAS)
    res.add_argument("--model")
    res.add_argument("--effort")
    res.add_argument("--fallback", help="comma-separated fallback backends for this invocation")
    res.add_argument("--available", help="comma-separated tool names the host exposes; "
                     "omit if unknown (then nothing is skipped as missing)")
    res.add_argument("--failed", action="append", metavar="BACKEND:REASON",
                     help="a backend that already failed, and why (repeatable)")
    res.add_argument("--executor-model", help="the executor's actual model id, if known")
    res.add_argument("--allow-same-family", action="store_true")

    ind = sub.add_parser("independence", help="judge executor/reviewer independence")
    ind.add_argument("--executor-model", required=True)
    ind.add_argument("--reviewer-model", required=True)

    show = sub.add_parser("show", help="resolve both roles and list the config files found")
    show.add_argument("--host", choices=HOSTS, required=True)
    show.add_argument("--stage-dir", default="molecule-design-stage")
    show.add_argument("--user-config", default=None)
    show.add_argument("--available", help="comma-separated tool names the host exposes")
    show.add_argument("--executor-model")

    sub.add_parser("backends", help="print the backend table")

    args = parser.parse_args(argv)
    try:
        if args.command == "backends":
            table = {
                name: {"family": spec["family"], "default_model": spec["default_model"],
                       "search": spec["search"], "direct": spec["tools"] is not None,
                       "agent_hud_client": spec["hud_client"]}
                for name, spec in BACKENDS.items()
            }
            print(json.dumps(table, indent=2))
            return 0
        if args.command == "show":
            report = show_setup(args)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if all(r.get("status") == "ok" for r in report["routes"].values()) else 3
        if args.command == "independence":
            print(json.dumps(independence(args.executor_model, args.reviewer_model)))
            return 0
        inline = {k: v for k, v in (("backend", args.backend), ("via", args.via),
                                    ("model", args.model), ("effort", args.effort),
                                    ("fallback", args.fallback)) if v is not None}
        route = resolve(
            role=args.role,
            host=args.host,
            project_file=os.path.join(args.stage_dir, "reviewer.json"),
            user_file=None if args.no_user_config else (args.user_config or user_config_path()),
            inline=inline,
            available=None if args.available is None
            else [t.strip() for t in args.available.split(",") if t.strip()],
            failed=parse_failed(args.failed),
            executor_model=args.executor_model,
            allow_same_family=args.allow_same_family,
        )
    except ConfigError as err:
        print(f"reviewer route error: {err}", file=sys.stderr)
        return 2
    print(json.dumps(route, ensure_ascii=False))
    return 0 if route["status"] == "ok" else 3


if __name__ == "__main__":
    sys.exit(main())

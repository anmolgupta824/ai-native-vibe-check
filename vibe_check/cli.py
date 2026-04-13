from __future__ import annotations

"""CLI entry point — battle, hooks, score, interview, generate-personas commands."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from . import __version__
from .interview import find_last_result, load_result, run_interview
from .personas import generate_personas_llm, generate_personas_sync, save_personas
from .providers import detect_provider
from .report import format_report, save_result
from .simulate import simulate_battle, simulate_hooks, simulate_score
from .init import run_init, run_regenerate


def _copy_to_clipboard(text: str) -> bool:
    """Try to copy text to clipboard. Returns True on success."""
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return True
    except ImportError:
        pass
    import subprocess, sys as _sys
    if _sys.platform == "darwin":
        try:
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        except Exception:
            pass
    return False


def _build_share_card(result: dict) -> str:
    """Build a shareable one-card summary from a result dict."""
    mode = result.get("mode", "")
    platform = result.get("platform", "linkedin").title()
    personas_used = result.get("personas_used", 0)
    sep = "━" * 40

    if mode == "battle":
        r = result["results"]
        winner = r["winner"]
        name = winner["post_file"]
        final = int(r["rankings"][0].get("final_score", r["rankings"][0].get("score_normalized", 0)))
        total = winner["total_personas"]
        share_pct = round(winner["share_count"] / total * 100) if total else 0
        save_pct = round(winner["save_count"] / total * 100) if total else 0
        comment_pct = round(winner["comment_count"] / total * 100) if total else 0
    elif mode == "score":
        r = result["results"]
        post = r["rankings"][0] if r["rankings"] else {}
        name = post.get("post_file", "post")
        final = int(post.get("final_score", post.get("score_normalized", 0)))
        total = post.get("total_personas", personas_used)
        share_pct = round(post.get("share_count", 0) / total * 100) if total else 0
        save_pct = round(post.get("save_count", 0) / total * 100) if total else 0
        comment_pct = round(post.get("comment_count", 0) / total * 100) if total else 0
    elif mode == "hooks":
        r = result["results"]
        winner = r["winner"]
        name = f'Hook #{winner["hook_index"] + 1}'
        top_rank = r["rankings"][0]
        final = int(top_rank.get("score_normalized", 0))
        total = top_rank.get("total_personas", personas_used)
        share_pct = 0
        save_pct = 0
        comment_pct = round(top_rank.get("would_stop", 0) / total * 100) if total else 0
    else:
        return ""

    lines = [
        sep,
        "🏆 VIBE CHECK RESULT",
        sep,
        "",
        f"{name} scored {final}/100",
        f"Tested against {personas_used} personas on {platform}",
        "",
    ]
    if mode == "hooks":
        lines.append(f"Would stop scrolling: {comment_pct}%")
    else:
        lines.append(f"Would share: {share_pct}% | Would save: {save_pct}% | Would comment: {comment_pct}%")
    lines += [
        "",
        sep,
        "⭐ github.com/anmolgupta824/ai-vibe-check",
        sep,
    ]
    return "\n".join(lines)


def _prompt_share_card(result: dict, no_share: bool = False) -> None:
    """Print share card and optionally copy to clipboard."""
    if no_share:
        return
    if not result or result.get("dry_run"):
        return

    card = _build_share_card(result)
    if not card:
        return

    print("")
    print(card)
    print("")
    try:
        answer = input("Share this? (copies to clipboard) [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if answer in ("", "y", "yes"):
        success = _copy_to_clipboard(card)
        if success:
            print("✅ Copied to clipboard!")
        else:
            print("Copied!")
            print(card)


def check_api_key(args):
    """Validate API key exists before running any LLM commands. Exits cleanly on failure."""
    provider_override = getattr(args, "provider", None)
    try:
        detect_provider(provider_override)
    except SystemExit:
        sys.exit(1)

REPO_ROOT = Path(__file__).parent.parent

# Reference audiences (tracked in git — defaults)
REF_AUDIENCES = {
    "linkedin": REPO_ROOT / "config" / "audiences" / "linkedin-tech.json",
    "threads": REPO_ROOT / "config" / "audiences" / "threads-broad-ai.json",
}

# User-generated audiences dir (gitignored)
USER_AUDIENCES_DIR = REPO_ROOT / "audiences"


def resolve_audience(args) -> Path:
    """Resolve audience config path from --audience or --platform flags.

    Lookup order:
    1. --audience flag (explicit path)
    2. audiences/custom-{platform}.json (user-generated via vibe-check init)
    3. config/audiences/{platform}-tech.json (reference default)
    """
    if hasattr(args, "audience") and args.audience:
        path = Path(args.audience)
        if not path.exists():
            # Try relative to audiences/ then config/audiences/
            for base in (USER_AUDIENCES_DIR, REPO_ROOT / "config" / "audiences"):
                alt = base / args.audience
                if alt.exists():
                    return alt
            print(f"❌ Audience file not found: {args.audience}")
            sys.exit(1)
        return path

    platform = getattr(args, "platform", "linkedin")

    # Check user-generated audience first
    user_audience = USER_AUDIENCES_DIR / f"custom-{platform}.json"
    if user_audience.exists():
        return user_audience

    # Fall back to reference audience
    if platform in REF_AUDIENCES:
        print("💡 Tip: Run 'vibe-check init' to generate a custom audience for your content.")
        return REF_AUDIENCES[platform]

    print(f"❌ No default audience for platform '{platform}'. Run 'vibe-check init' or use --audience.")
    sys.exit(1)


def load_posts(paths: list[str]) -> list[dict]:
    """Load post content from file paths."""
    posts = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            # Load all .txt and .md files from directory
            for f in sorted(path.iterdir()):
                if f.suffix in (".txt", ".md"):
                    posts.append({"file": f.name, "content": f.read_text().strip()})
        elif path.exists():
            posts.append({"file": path.name, "content": path.read_text().strip()})
        else:
            print(f"⚠️  File not found: {p}")
    return posts


def cmd_battle(args):
    """Run battle mode."""
    posts = load_posts(args.posts)
    if len(posts) < 2:
        print("❌ Battle mode needs at least 2 posts.")
        sys.exit(1)

    if not args.dry_run:
        check_api_key(args)

    audience_path = resolve_audience(args)
    print(f"⚔️  Loading {len(posts)} posts for battle...")

    result = asyncio.run(simulate_battle(
        posts=posts,
        audience_path=audience_path,
        model_override=args.model,
        preset=args.preset,
        agents=args.agents,
        dry_run=args.dry_run,
        provider_override=getattr(args, "provider", None),
    ))

    print(format_report(result))

    if not result.get("dry_run"):
        path = save_result(result)
        print(f"\n💾 Results saved: {path}")
        _prompt_share_card(result, no_share=getattr(args, "no_share", False))


def cmd_hooks(args):
    """Run hooks mode."""
    if not args.post:
        print("❌ Hooks mode requires --post <file>")
        sys.exit(1)

    post_path = Path(args.post)
    if not post_path.exists():
        print(f"❌ Post file not found: {args.post}")
        sys.exit(1)

    post = {"file": post_path.name, "content": post_path.read_text().strip()}
    hooks = args.hook

    if not hooks or len(hooks) < 2:
        print("❌ Hooks mode needs at least 2 hooks. Use --hook '...' --hook '...'")
        sys.exit(1)

    if not args.dry_run:
        check_api_key(args)

    audience_path = resolve_audience(args)
    print(f"🎣 Testing {len(hooks)} hooks...")

    result = asyncio.run(simulate_hooks(
        post=post,
        hooks=hooks,
        audience_path=audience_path,
        model_override=args.model,
        preset=args.preset,
        agents=args.agents,
        dry_run=args.dry_run,
        provider_override=getattr(args, "provider", None),
    ))

    print(format_report(result))

    if not result.get("dry_run"):
        path = save_result(result)
        print(f"\n💾 Results saved: {path}")
        _prompt_share_card(result, no_share=getattr(args, "no_share", False))


def cmd_score(args):
    """Score a single post."""
    posts = load_posts(args.posts)
    if len(posts) != 1:
        print(f"❌ Score mode takes exactly 1 post, got {len(posts)}.")
        sys.exit(1)

    if not args.dry_run:
        check_api_key(args)

    audience_path = resolve_audience(args)
    print(f"📝 Scoring post...")

    result = asyncio.run(simulate_score(
        post=posts[0],
        audience_path=audience_path,
        model_override=args.model,
        preset=args.preset,
        agents=args.agents,
        dry_run=args.dry_run,
        provider_override=getattr(args, "provider", None),
    ))

    print(format_report(result))

    if not result.get("dry_run"):
        path = save_result(result)
        print(f"\n💾 Results saved: {path}")
        _prompt_share_card(result, no_share=getattr(args, "no_share", False))


def cmd_interview(args):
    """Run follow-up interviews."""
    if args.last:
        result = find_last_result()
    elif args.run:
        result = load_result(args.run)
    else:
        print("❌ Interview needs --last or --run <id>")
        sys.exit(1)

    if not result:
        print("❌ No previous results found. Run a battle or score first.")
        sys.exit(1)

    check_api_key(args)

    print(f"🎙️  Interviewing personas from {result.get('id', 'last run')}...")

    interview_result = asyncio.run(run_interview(
        result=result,
        question=args.ask,
        filter_action=args.filter,
        segment=args.segment,
        post_file=args.post,
        model_override=args.model,
        preset=args.preset,
        provider_override=getattr(args, "provider", None),
    ))

    if "error" in interview_result:
        print(f"❌ {interview_result['error']}")
        sys.exit(1)

    print(format_report(interview_result))

    path = save_result(interview_result)
    print(f"\n💾 Interview saved: {path}")


def cmd_init(args):
    """Run the guided init flow."""
    run_init()


def cmd_regenerate(args):
    """Regenerate an existing audience."""
    run_regenerate(
        audience_path=getattr(args, "audience", None),
        count=getattr(args, "count", None),
        fresh=getattr(args, "fresh", False),
    )


def cmd_generate_personas(args):
    """Generate personas from audience config."""
    audience_path = resolve_audience(args)
    with open(audience_path) as f:
        audience = json.load(f)

    if args.llm:
        print(f"🧠 Generating {audience['total_personas']} personas with LLM...")
        personas = asyncio.run(generate_personas_llm(
            audience=audience,
            model_override=args.model,
            preset=args.preset,
        ))
    else:
        print(f"⚡ Generating {audience['total_personas']} personas (deterministic)...")
        personas = generate_personas_sync(audience)

    path = save_personas(audience["name"], personas)
    print(f"✅ Generated {len(personas)} personas → {path}")


def cmd_log_outcome(args):
    """Log actual post performance after publishing.

    Two modes:
    1. With run: Attach outcome to a previous battle/score run (validates prediction)
    2. Standalone: Log outcome without a prior run (no prediction to validate)
    """
    from datetime import datetime, timezone

    outcome = {
        "posted": args.posted,
        "actual": {
            "impressions": args.impressions,
            "likes": args.likes or 0,
            "comments": args.comments or 0,
            "saves": args.saves or 0,
            "shares": args.shares or 0,
        },
        "swarm_predicted_rank": None,
        "swarm_score": None,
        "accurate": None,
    }

    # Try to find a matching run
    result = None
    if args.run:
        result = load_result(args.run)
    elif not args.standalone:
        result = find_last_result()

    if result:
        # Attach outcome to existing run
        if result.get("results", {}).get("rankings"):
            for i, rank in enumerate(result["results"]["rankings"]):
                if rank.get("post_file") == args.posted:
                    outcome["swarm_predicted_rank"] = i + 1
                    outcome["swarm_score"] = rank.get("score_normalized")
                    break

        result["outcome"] = outcome
        path = save_result(result)
        print(f"✅ Outcome logged → {path}")
        print(f"   Posted: {args.posted}")
        print(f"   Impressions: {args.impressions:,}")
        if outcome["swarm_score"]:
            print(f"   Swarm score: {int(outcome['swarm_score'])}/100")
        elif not args.standalone:
            print(f"   ⚠️  Post '{args.posted}' not found in run rankings. Use --standalone to log without a run.")
    else:
        # Standalone mode — no prior run needed
        standalone_result = {
            "id": f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-standalone-{args.posted.replace('.', '-')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "standalone-outcome",
            "outcome": outcome,
        }
        path = save_result(standalone_result)
        print(f"✅ Standalone outcome logged → {path}")
        print(f"   Posted: {args.posted}")
        print(f"   Impressions: {args.impressions:,}")
        print(f"   (No swarm prediction — standalone mode)")


def cmd_stats(args):
    """Show accuracy stats across all runs with outcomes."""
    results_dir = Path(__file__).parent.parent / "results"
    if not results_dir.exists():
        print("❌ No results directory found.")
        sys.exit(1)

    runs_with_outcomes = []
    for d in sorted(results_dir.iterdir()):
        result_file = d / "result.json"
        if result_file.exists():
            with open(result_file) as f:
                result = json.load(f)
            if result.get("outcome"):
                runs_with_outcomes.append(result)

    if not runs_with_outcomes:
        print("📊 No outcomes logged yet. Use 'vibe-check log-outcome' after posting.")
        return

    total = len(runs_with_outcomes)
    correct = sum(1 for r in runs_with_outcomes if r["outcome"].get("accurate"))

    print("")
    print("📊 VIBE CHECK — ACCURACY REPORT")
    print("─" * 40)
    print(f"Total runs with outcomes: {total}")
    print(f"Correct predictions: {correct}/{total}")
    print("")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="vibe-check",
        description="AI focus group for content creators. Score your posts before publishing.",
    )
    parser.add_argument("--version", action="version", version=f"vibe-check {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common args
    def add_common_args(p):
        p.add_argument("--platform", choices=["linkedin", "threads"], default="linkedin")
        p.add_argument("--audience", help="Path to audience JSON config")
        p.add_argument("--model", help="Override model (e.g., 'openai/gpt-4o-mini')")
        p.add_argument("--preset", choices=["free", "cheap", "quality", "local"])
        p.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "groq", "gemini", "deepseek"],
                       help="Force a specific provider (default: auto-detect from .env)")
        p.add_argument("--agents", type=int, help="Override persona count")
        p.add_argument("--dry-run", action="store_true", help="Estimate cost without running")

    # init
    p_init = subparsers.add_parser("init", help="Guided setup: build your audience in 2 minutes")
    p_init.set_defaults(func=cmd_init)

    # regenerate
    p_regen = subparsers.add_parser("regenerate", help="Regenerate an existing audience")
    p_regen.add_argument("--audience", help="Path to audience JSON to regenerate")
    p_regen.add_argument("--count", type=int, help="Override persona count")
    p_regen.add_argument("--fresh", action="store_true", help="Start fresh (runs full init)")
    p_regen.set_defaults(func=cmd_regenerate)

    # battle
    p_battle = subparsers.add_parser("battle", help="Compare 2-5 post drafts")
    add_common_args(p_battle)
    p_battle.add_argument("posts", nargs="+", help="Post files or directory")
    p_battle.add_argument("--no-share", action="store_true", help="Skip the share card prompt after results")
    p_battle.set_defaults(func=cmd_battle)

    # hooks
    p_hooks = subparsers.add_parser("hooks", help="Test hook variants for a post")
    add_common_args(p_hooks)
    p_hooks.add_argument("--post", required=True, help="Post file to test hooks for")
    p_hooks.add_argument("--hook", action="append", help="Hook text (use multiple --hook flags)")
    p_hooks.add_argument("--no-share", action="store_true", help="Skip the share card prompt after results")
    p_hooks.set_defaults(func=cmd_hooks)

    # score
    p_score = subparsers.add_parser("score", help="Score a single post")
    add_common_args(p_score)
    p_score.add_argument("posts", nargs=1, help="Post file to score")
    p_score.add_argument("--no-share", action="store_true", help="Skip the share card prompt after results")
    p_score.set_defaults(func=cmd_score)

    # interview
    p_interview = subparsers.add_parser("interview", help="Follow up with personas")
    p_interview.add_argument("--last", action="store_true", help="Use most recent run")
    p_interview.add_argument("--run", help="Specific run ID")
    p_interview.add_argument("--post", help="Which post to interview about (filename from battle)")
    p_interview.add_argument("--filter", help="Filter by action (scroll_past, share, save, etc)")
    p_interview.add_argument("--segment", help="Filter by segment (CTO, Engineer, etc)")
    p_interview.add_argument("--ask", help="Custom question to ask personas")
    p_interview.add_argument("--model", help="Override model")
    p_interview.add_argument("--preset", choices=["free", "cheap", "quality", "local"])
    p_interview.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "groq", "gemini", "deepseek"],
                             help="Force a specific provider")
    p_interview.set_defaults(func=cmd_interview)

    # generate-personas
    p_gen = subparsers.add_parser("generate-personas", help="Generate personas from audience config")
    p_gen.add_argument("--platform", choices=["linkedin", "threads"], default="linkedin")
    p_gen.add_argument("--audience", help="Path to audience JSON config")
    p_gen.add_argument("--llm", action="store_true", help="Use LLM for richer personas (costs API calls)")
    p_gen.add_argument("--model", help="Override model")
    p_gen.add_argument("--preset", choices=["free", "cheap", "quality", "local"])
    p_gen.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "groq", "gemini", "deepseek"],
                       help="Force a specific provider")
    p_gen.set_defaults(func=cmd_generate_personas)

    # log-outcome
    p_outcome = subparsers.add_parser("log-outcome", help="Log actual post performance")
    p_outcome.add_argument("--run", help="Run ID (default: last run)")
    p_outcome.add_argument("--standalone", action="store_true",
                           help="Log outcome without a prior run (no prediction validation)")
    p_outcome.add_argument("--posted", required=True, help="Which post was published")
    p_outcome.add_argument("--impressions", type=int, required=True)
    p_outcome.add_argument("--likes", type=int, default=0)
    p_outcome.add_argument("--comments", type=int, default=0)
    p_outcome.add_argument("--saves", type=int, default=0)
    p_outcome.add_argument("--shares", type=int, default=0)
    p_outcome.set_defaults(func=cmd_log_outcome)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show accuracy report")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()

"""Report formatting — terminal output, markdown, JSON."""

import json
from pathlib import Path


def format_bar(score: float, max_score: float = 10, width: int = 20) -> str:
    """Create a visual bar chart."""
    filled = int((score / max_score) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def format_battle_report(result: dict) -> str:
    """Format battle mode results for terminal output."""
    r = result["results"]
    rankings = r["rankings"]
    responses = r["persona_responses"]
    winner = r["winner"]

    lines = []
    lines.append("")
    lines.append("⚔️  VIBE CHECK — BATTLE MODE")
    lines.append(f"Platform: {result['platform'].title()} | Audience: {result['audience']} ({result['personas_used']} personas)")
    lines.append("─" * 50)
    lines.append("")

    # Winner
    lines.append(f"🏆 WINNER: {winner['post_file']}")
    lines.append("")

    # Rankings with triple score
    lines.append("📊 Rankings:")
    for i, rank in enumerate(rankings):
        marker = "  ← SHIP THIS" if i == 0 else ""
        final = int(rank.get("final_score", rank.get("score_normalized", 0)))
        bar = format_bar(final / 10)
        lines.append(f"  {i+1}. {rank['post_file']} {bar}  {final}/100{marker}")
        content = int(rank.get("content_score", 0))
        engagement = int(rank.get("engagement_score", 0))
        lines.append(f"     Content: {content}/100 | Engagement: {engagement}/100 | Final: {final}/100")
    lines.append("")

    # Engagement breakdown for winner
    lines.append(f"📈 Engagement Breakdown ({winner['post_file']}):")
    total = winner["total_personas"]
    engage = total - winner["scroll_past_count"]
    lines.append(f"  Would engage:  {engage}/{total} ({_pct(engage, total)})")
    lines.append(f"  Would share:   {winner['share_count']}/{total} ({_pct(winner['share_count'], total)})")
    lines.append(f"  Would save:    {winner['save_count']}/{total} ({_pct(winner['save_count'], total)})")
    lines.append(f"  Would comment: {winner['comment_count']}/{total} ({_pct(winner['comment_count'], total)})")
    lines.append(f"  Would scroll:  {winner['scroll_past_count']}/{total} ({_pct(winner['scroll_past_count'], total)})")
    lines.append("")

    # Top reactions (from winner's responses)
    winner_responses = [r for r in responses if r.get("post_file") == winner["post_file"]]
    top_reactions = sorted(
        [r for r in winner_responses if r.get("action") != "scroll_past"],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:3]

    if top_reactions:
        lines.append("💬 Top Reactions:")
        for r in top_reactions:
            reason = r.get("reason", "No reason given")
            lines.append(f'  {r["persona"]}: "{reason}"')
        lines.append("")

    # Why losers lost
    if len(rankings) > 1:
        loser = rankings[-1]
        loser_responses = [r for r in responses if r.get("post_file") == loser["post_file"]]
        scroll_pasters = [r for r in loser_responses if r.get("action") == "scroll_past"][:2]
        if scroll_pasters:
            lines.append(f"⚠️  Why {loser['post_file']} Lost:")
            for r in scroll_pasters:
                reason = r.get("reason", "No reason given")
                lines.append(f'  {r["persona"]}: "{reason}"')
            lines.append("")

    # Improvement suggestions (most common from winner)
    improvements = [r.get("improvement", "") for r in winner_responses if r.get("improvement") and r["improvement"] != "N/A (parse error)"]
    if improvements:
        lines.append("💡 Suggestions to Improve Winner:")
        seen = set()
        count = 0
        for imp in improvements:
            if imp not in seen and count < 3:
                seen.add(imp)
                count += 1
                lines.append(f"  {count}. {imp}")
        lines.append("")

    lines.append(f"Model: {result['model']} | Calls: {result['total_api_calls']}")
    return "\n".join(lines)


def format_hooks_report(result: dict) -> str:
    """Format hooks mode results for terminal output."""
    r = result["results"]
    rankings = r["rankings"]
    winner = r["winner"]

    lines = []
    lines.append("")
    lines.append("🎣 VIBE CHECK — HOOKS MODE")
    lines.append(f"Platform: {result['platform'].title()} | Audience: {result['audience']} ({result['personas_used']} personas)")
    lines.append("─" * 50)
    lines.append("")

    lines.append(f"🏆 WINNING HOOK: #{winner['hook_index'] + 1}")
    lines.append(f'   "{winner["hook"]}"')
    lines.append("")

    lines.append("📊 Hook Rankings:")
    for i, rank in enumerate(rankings):
        marker = "  ← USE THIS" if i == 0 else ""
        bar = format_bar(rank["score"])
        score_100 = int(rank["score_normalized"])
        lines.append(f'  {i+1}. "{rank["hook"][:60]}..." {bar}  {score_100}/100{marker}')
        stop_pct = _pct(rank["would_stop"], rank["total_personas"])
        lines.append(f"     Would stop: {rank['would_stop']}/{rank['total_personas']} ({stop_pct})")
    lines.append("")

    lines.append(f"Model: {result['model']} | Hooks tested: {result['hooks_tested']}")
    return "\n".join(lines)


def format_score_report(result: dict) -> str:
    """Format single-post score results."""
    r = result["results"]
    rankings = r["rankings"]
    post = rankings[0] if rankings else {}

    lines = []
    lines.append("")
    lines.append("📝 VIBE CHECK — SCORE MODE")
    lines.append(f"Platform: {result['platform'].title()} | Audience: {result['audience']} ({result['personas_used']} personas)")
    lines.append("─" * 50)
    lines.append("")

    content = int(post.get("content_score", 0))
    engagement = int(post.get("engagement_score", 0))
    final = int(post.get("final_score", post.get("score_normalized", 0)))
    bar = format_bar(final / 10)
    lines.append(f"  Content Score:    {format_bar(content / 10)}  {content}/100  (what personas rated it)")
    lines.append(f"  Engagement Score: {format_bar(engagement / 10)}  {engagement}/100  (weighted by actions)")
    lines.append(f"  Final Score:      {bar}  {final}/100  (40/60 blend)")
    lines.append("")

    if final >= 75:
        lines.append("✅ Ship it. This post is likely to perform well.")
    elif final >= 65:
        lines.append("🔶 Decent. Consider revisions before posting.")
    else:
        lines.append("🔴 Weak. Revise or kill this draft.")
    lines.append("")

    total = post.get("total_personas", 0)
    if total:
        lines.append("📈 Engagement Breakdown:")
        lines.append(f"  Would engage:  {total - post.get('scroll_past_count', 0)}/{total}")
        lines.append(f"  Would share:   {post.get('share_count', 0)}/{total}")
        lines.append(f"  Would save:    {post.get('save_count', 0)}/{total}")
        lines.append(f"  Would comment: {post.get('comment_count', 0)}/{total}")
        lines.append(f"  Would scroll:  {post.get('scroll_past_count', 0)}/{total}")
    lines.append("")

    # Top responses
    responses = r.get("persona_responses", [])
    positive = sorted(
        [r for r in responses if r.get("action") != "scroll_past"],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:3]
    if positive:
        lines.append("💬 Top Reactions:")
        for resp in positive:
            lines.append(f'  {resp["persona"]}: "{resp.get("reason", "")}"')
        lines.append("")

    negative = [r for r in responses if r.get("action") == "scroll_past"][:2]
    if negative:
        lines.append("⚠️  Would Scroll Past:")
        for resp in negative:
            lines.append(f'  {resp["persona"]}: "{resp.get("reason", "")}"')
        lines.append("")

    return "\n".join(lines)


def format_interview_report(result: dict) -> str:
    """Format interview mode results."""
    lines = []
    lines.append("")
    lines.append(f'🎙️  INTERVIEW — "{result["question"]}"')

    filter_desc = []
    if result.get("filter"):
        filter_desc.append(f'filter: {result["filter"]}')
    if result.get("segment"):
        filter_desc.append(f'segment: {result["segment"]}')
    if filter_desc:
        lines.append(f"    {', '.join(filter_desc)} ({result['personas_interviewed']} personas)")

    lines.append("─" * 50)
    lines.append("")

    for resp in result["responses"]:
        lines.append(f'{resp["persona"]}: "{resp["response"]}"')
        lines.append("")

    # Try to identify patterns
    lines.append(f"📊 {result['personas_interviewed']} personas interviewed.")
    lines.append(f"Model: {result['model']}")
    return "\n".join(lines)


def format_dry_run(result: dict) -> str:
    """Format dry run output."""
    lines = []
    lines.append("")
    lines.append("📊 DRY RUN:")
    lines.append(f"  Agents: {result['agents']}")
    if "posts" in result:
        lines.append(f"  Posts: {result['posts']}")
    if "hooks" in result:
        lines.append(f"  Hooks: {result['hooks']}")
    lines.append(f"  API calls: {result['api_calls']}")
    if "estimated_tokens" in result:
        lines.append(f"  Estimated tokens: ~{result['estimated_tokens']:,}")
    lines.append(f"  Model: {result['model']}")
    return "\n".join(lines)


def format_report(result: dict) -> str:
    """Auto-format based on result mode."""
    if result.get("dry_run"):
        return format_dry_run(result)

    mode = result.get("mode", "")
    if mode == "battle":
        return format_battle_report(result)
    elif mode == "hooks":
        return format_hooks_report(result)
    elif mode == "score":
        return format_score_report(result)
    elif mode == "interview":
        return format_interview_report(result)
    else:
        return json.dumps(result, indent=2)


def save_result(result: dict) -> Path:
    """Save result to results/ directory."""
    results_dir = Path(__file__).parent.parent / "results"
    run_id = result.get("id", "unknown")
    run_dir = results_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    result_path = run_dir / "result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    return result_path


def _pct(n: int, total: int) -> str:
    """Format as percentage string."""
    if total == 0:
        return "0%"
    return f"{round(n / total * 100)}%"

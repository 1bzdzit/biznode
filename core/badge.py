def get_badge(status):
    badges = {
        "VERIFIED": "🔵 1BZ VERIFIED",
        "TRUSTED": "🟢 1BZ TRUSTED NODE",
        "ENTERPRISE": "🟣 1BZ ENTERPRISE",
        "UNVERIFIED": "🟡 SELF DECLARED"
    }
    return badges.get(status, "🟡 SELF DECLARED")
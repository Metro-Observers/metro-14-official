using Robust.Shared;
using Robust.Shared.Configuration;

namespace Content.Shared.CCVar;

/// <summary>
/// Metro-14 fork CVars. Kept separate from upstream CCVars per fork guidance.
/// </summary>
[CVarDefs]
public sealed class Metro14CVars
{
    /// <summary>
    /// Adds this many players to /status "players" for local hub reporting tests.
    /// Applied only when hub.advertise is false, so a live hub advertise cannot carry a faked count.
    /// Default 0 = no change.
    /// </summary>
    public static readonly CVarDef<int> StatusFakePlayers =
        CVarDef.Create("metro14.status_fake_players", 0, CVar.SERVERONLY);
}

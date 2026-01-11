using Content.Client.Gandon.Overlays;
using Content.Shared.Gandon.Components;
using Content.Shared.Gandon.Systems;
using Content.Shared.StatusEffect;
using Robust.Client.GameObjects;
using Robust.Client.Graphics;
using Robust.Client.Player;
using Robust.Shared.Player;

namespace Content.Client.Gandon.Systems;

public sealed class GandonSystem : SharedGandonSystem
{
    [Dependency] private readonly IPlayerManager _player = default!;
    [Dependency] private readonly IOverlayManager _overlayMan = default!;
    [Dependency] private readonly SpriteSystem _spriteSystem = default!;
    [Dependency] private readonly StatusEffectsSystem _statusEffectsSystem = default!;

    private GandonHallutinationsOverlay _overlay = default!;

    public override void Initialize()
    {
        base.Initialize();

        SubscribeLocalEvent<GandonHallucinationsStatusEffectComponent, ComponentInit>(OnInit);
        SubscribeLocalEvent<GandonHallucinationsStatusEffectComponent, ComponentShutdown>(OnShutdown);
        SubscribeLocalEvent<GandonHallucinationsStatusEffectComponent, LocalPlayerAttachedEvent>(OnPlayerAttached);
        SubscribeLocalEvent<GandonHallucinationsStatusEffectComponent, LocalPlayerDetachedEvent>(OnPlayerDetached);

        _overlay = new(_spriteSystem, _statusEffectsSystem);
    }

    private void OnInit(EntityUid uid, GandonHallucinationsStatusEffectComponent component, ComponentInit args)
    {
        if (_player.LocalEntity == null)
            return;

        _overlayMan.AddOverlay(_overlay);
    }

    private void OnShutdown(EntityUid uid, GandonHallucinationsStatusEffectComponent component, ComponentShutdown args)
    {
        if (_player.LocalEntity == null)
            return;

        _overlay.PercentComplete = 0;
        _overlayMan.RemoveOverlay(_overlay);
    }

    private void OnPlayerAttached(EntityUid uid, GandonHallucinationsStatusEffectComponent component, LocalPlayerAttachedEvent args)
    {
        _overlayMan.AddOverlay(_overlay);
    }

    private void OnPlayerDetached(EntityUid uid, GandonHallucinationsStatusEffectComponent component, LocalPlayerDetachedEvent args)
    {
        _overlay.PercentComplete = 0;
        _overlayMan.RemoveOverlay(_overlay);
    }
}

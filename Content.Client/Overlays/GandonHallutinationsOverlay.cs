using System.Numerics;
using Content.Shared.Gandon.Components;
using Content.Shared.Gandon.Systems;
using Content.Shared.StatusEffect;
using Robust.Client.GameObjects;
using Robust.Client.Graphics;
using Robust.Client.Player;
using Robust.Shared.Enums;
using Robust.Shared.Prototypes;
using Robust.Shared.Timing;
using Robust.Shared.Utility;

namespace Content.Client.Gandon.Overlays;

public sealed class GandonHallutinationsOverlay : Overlay
{
    private static readonly ProtoId<ShaderPrototype> Shader = "GandonHallutinations";
    private readonly ShaderInstance _gandonHallutinationsShader;

    [Dependency] private readonly IEntityManager _entityManager = default!;
    [Dependency] private readonly IPrototypeManager _prototypeManager = default!;
    [Dependency] private readonly IPlayerManager _playerManager = default!;
    [Dependency] private readonly IGameTiming _timing = default!;

    private readonly StatusEffectsSystem _statusEffectsSystem;

    private Texture _noiseTexture;

    public override OverlaySpace Space => OverlaySpace.WorldSpace;
    public override bool RequestScreenTexture => true;

    private float _currentVisualPercent;
    public float PercentComplete;

    public GandonHallutinationsOverlay(SpriteSystem sprite, StatusEffectsSystem statusEffectsSystem)
    {
        IoCManager.InjectDependencies(this);
        _statusEffectsSystem = statusEffectsSystem;
        _gandonHallutinationsShader = _prototypeManager.Index(Shader).InstanceUnique();
        var curTime = _timing.RealTime;
        _noiseTexture = sprite.GetFrame(new SpriteSpecifier.Texture(new ResPath("/Textures/_Metro14/Negri/new_fast_noise_lite.png")), curTime);
    }

    protected override void FrameUpdate(FrameEventArgs args)
    {
        var playerEntity = _playerManager.LocalEntity;

        if (playerEntity == null)
            return;

        if (!_entityManager.HasComponent<GandonHallucinationsStatusEffectComponent>(playerEntity)
            || !_entityManager.TryGetComponent<StatusEffectsComponent>(playerEntity, out var status))
            return;

        if (!_statusEffectsSystem.TryGetTime(playerEntity.Value, SharedGandonSystem.StatusEffectGandonHallucinations, out var time, status))
            return;

        var curTime = _timing.CurTime;
        var lastsFor = (float)(time.Value.Item2 - time.Value.Item1).TotalSeconds;
        var timeDone = (float)(curTime - time.Value.Item1).TotalSeconds;

        var rawPercent = timeDone / lastsFor;

        _currentVisualPercent = MathHelper.Lerp(_currentVisualPercent, rawPercent, 0.05f);
        PercentComplete = _currentVisualPercent;
    }

    protected override bool BeforeDraw(in OverlayDrawArgs args)
    {
        if (!_entityManager.TryGetComponent(_playerManager.LocalEntity, out EyeComponent? eyeComp))
            return false;

if (!_entityManager.HasComponent<GandonHallucinationsStatusEffectComponent>(_playerManager.LocalEntity))
            return false;

        return args.Viewport.Eye == eyeComp.Eye && PercentComplete < 0.999f;
    }

    protected override void Draw(in OverlayDrawArgs args)
    {
        if (ScreenTexture == null)
            return;

        var handle = args.WorldHandle;

        _gandonHallutinationsShader.SetParameter("SCREEN_TEXTURE", ScreenTexture);
        _gandonHallutinationsShader.SetParameter("noise_tex", _noiseTexture);
        _gandonHallutinationsShader.SetParameter("percentComplete", PercentComplete);
        _gandonHallutinationsShader.SetParameter("burn_size", 0.2f);
        _gandonHallutinationsShader.SetParameter("shit_size", 0.5f);
        _gandonHallutinationsShader.SetParameter("burn_color", new Vector4(0.0f, 0.0f, 0.0f, 1.0f));

        handle.UseShader(_gandonHallutinationsShader);
        handle.DrawRect(args.WorldBounds, Color.White);
        handle.UseShader(null);
    }
}

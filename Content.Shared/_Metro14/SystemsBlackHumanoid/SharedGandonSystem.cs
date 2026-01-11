using Content.Shared.Actions;
using Content.Shared.Bed.Sleep;
using Content.Shared.Gandon.Components;
using Content.Shared.Gandon.Events;
using Content.Shared.Physics;
using Content.Shared.Stealth;
using Content.Shared.Stealth.Components;
using Content.Shared.Stunnable;
using Content.Shared.Throwing;
using Content.Shared.Weapons.Melee.Events;
using Robust.Shared.Physics.Components;
using Robust.Shared.Prototypes;

namespace Content.Shared.Gandon.Systems;

public abstract class SharedGandonSystem : EntitySystem
{
    [Dependency] private readonly SharedActionsSystem _actionsSystem = default!;
    [Dependency] private readonly EntityLookupSystem _lookupSystem = default!;
    [Dependency] private readonly StatusEffect.StatusEffectsSystem Status = default!;
    [Dependency] private readonly StatusEffectNew.StatusEffectsSystem ZalupaStatus = default!;
    [Dependency] private readonly ThrowingSystem _throwingSystem = default!;
    [Dependency] private readonly SharedTransformSystem _xform = default!;
    [Dependency] private readonly SharedStealthSystem _stealthSystem = default!;
    [Dependency] private readonly SharedStunSystem _stunSystem = default!;

    public static readonly EntProtoId StatusEffectGandonHallucinations = "StatusEffectGandonHallucinations";

    public override void Initialize()
    {
        SubscribeLocalEvent<GandonComponent, MapInitEvent>(OnMapInit);
        SubscribeLocalEvent<GandonComponent, ComponentRemove>(OnCompRemove);

        SubscribeLocalEvent<GandonComponent, GandonEuthanasiaEvent>(OnEuthanasia);
        SubscribeLocalEvent<GandonComponent, ActionGandonStandoff>(OnStandoff);
        SubscribeLocalEvent<GandonComponent, ActionGandonStealth>(OnStealth);
        SubscribeLocalEvent<GandonComponent, ActionGandonHallucinations>(OnHallucinations);

        SubscribeLocalEvent<GandonComponent, MeleeAttackEvent>(OnMeleeAttack);
        SubscribeLocalEvent<GandonComponent, AttackedEvent>(OnAttacked);
    }

    private void OnEuthanasia(EntityUid uid, GandonComponent component, GandonEuthanasiaEvent args)
    {
        if (args.Handled)
            return;

        var targetCoords = args.Target;

        var entitiesInRange = _lookupSystem.GetEntitiesInRange(targetCoords, component.EuthanasiaSleepRadius, LookupFlags.Dynamic);
        entitiesInRange.Remove(uid);

        foreach (var entityUid in entitiesInRange)
        {
            ZalupaStatus.TryAddStatusEffectDuration(entityUid, SleepingSystem.StatusEffectForcedSleeping, TimeSpan.FromSeconds(component.EuthanasiaSleepDuration));
        }

        args.Handled = true;
    }

    private void OnStandoff(EntityUid uid, GandonComponent component, ActionGandonStandoff args)
    {
        if (args.Handled)
            return;

        RevealGandon(uid, component);

        var performerCoords = Transform(args.Performer).Coordinates;

        var entitiesInRange = _lookupSystem.GetEntitiesInRange(performerCoords, component.StandoffAreaRadius, LookupFlags.Dynamic);
        entitiesInRange.Remove(uid);

        var physQuery = GetEntityQuery<PhysicsComponent>();
        var xformQuery = GetEntityQuery<TransformComponent>();

        var worldPos = _xform.GetWorldPosition(uid, xformQuery);

        foreach (var entityUid in entitiesInRange)
        {
            if (physQuery.TryGetComponent(entityUid, out var phys)
                && (phys.CollisionMask & (int) CollisionGroup.GhostImpassable) != 0)
                continue;

            var direction = _xform.GetWorldPosition(entityUid, xformQuery) - worldPos;
            _stunSystem.TryUpdateStunDuration(entityUid, TimeSpan.FromSeconds(component.StandoffStunDuration));
            _stunSystem.TryKnockdown(entityUid, TimeSpan.FromSeconds(component.StandoffKnockdownDuration), autoStand: false, force: true);
            _throwingSystem.TryThrow(entityUid, direction.Normalized(), component.StandoffThrowSpeed, uid, 0, recoil: false);
        }

        args.Handled = true;
    }

    private void OnStealth(EntityUid uid, GandonComponent component, ActionGandonStealth args)
    {
        if (args.Handled)
            return;

        var stealth = EnsureComp<StealthComponent>(uid);

        component.StealthToggled = !component.StealthToggled;
        Dirty(uid, component);

        _stealthSystem.SetEnabled(uid, component.StealthToggled, stealth);
        _actionsSystem.SetToggled(component.StealthActionEntity, component.StealthToggled);

        CreateDelay(component, TimeSpan.FromSeconds(component.StealthCooldown)); // Dear friend,

        args.Handled = true;
    }

    private void OnHallucinations(EntityUid uid, GandonComponent component, ActionGandonHallucinations args)
    {
        if (args.Handled)
            return;

        var performerCoords = Transform(args.Performer).Coordinates;

        var entitiesInRange = _lookupSystem.GetEntitiesInRange(performerCoords, component.HallucinationsRadius, LookupFlags.Dynamic);
        entitiesInRange.Remove(uid);

        foreach (var entityUid in entitiesInRange)
        {
            _stunSystem.TryUpdateStunDuration(entityUid, TimeSpan.FromSeconds(component.HallucinationStunDuration));
            _stunSystem.TryKnockdown(entityUid, TimeSpan.FromSeconds(component.HallucinationKnockdownDuration), autoStand: false, force: true);
            Status.TryAddStatusEffect<GandonHallucinationsStatusEffectComponent>(entityUid, StatusEffectGandonHallucinations, TimeSpan.FromSeconds(component.HallucinationDuration), false);
        }

        args.Handled = true;
    }

    private void OnMeleeAttack(EntityUid uid, GandonComponent component, ref MeleeAttackEvent args)
    {
        RevealGandon(uid, component);
    }

    private void OnAttacked(EntityUid uid, GandonComponent component, AttackedEvent args)
    {
        RevealGandon(uid, component);
    }

    private void RevealGandon(EntityUid uid, GandonComponent component)
    {
        CreateDelay(component, TimeSpan.FromSeconds(component.RevealedStealthCooldown));
        _actionsSystem.SetToggled(component.StealthActionEntity, false);

        var stealth = EnsureComp<StealthComponent>(uid);

        component.StealthToggled = false;
        Dirty(uid, component);

        _stealthSystem.SetEnabled(uid, component.StealthToggled, stealth);
    }

    private void CreateDelay(GandonComponent component, TimeSpan cooldown)
    {
        _actionsSystem.SetUseDelay(component.StealthActionEntity, cooldown);
        _actionsSystem.StartUseDelay(component.StealthActionEntity);
    }

    private void OnMapInit(EntityUid uid, GandonComponent component, MapInitEvent args)
    {
        _actionsSystem.AddAction(uid, ref component.EuthanasiaActionEntity, component.EuthanasiaActionPrototype);
        _actionsSystem.AddAction(uid, ref component.StandoffActionEntity,component.StandoffActionPrototype);
        _actionsSystem.AddAction(uid, ref component.StealthActionEntity,component.StealthActionPrototype);
        _actionsSystem.AddAction(uid, ref component.HallucinationsActionEntity,component.HallucinationsActionPrototype);

        var stealth = EnsureComp<StealthComponent>(uid);
        _stealthSystem.SetEnabled(uid, component.StealthToggled, stealth);
        _actionsSystem.SetToggled(component.StealthActionEntity, component.StealthToggled);
    }

    private void OnCompRemove(EntityUid uid, GandonComponent component, ComponentRemove args)
    {
        _actionsSystem.RemoveAction(uid, component.EuthanasiaActionEntity);
        _actionsSystem.RemoveAction(uid, component.StandoffActionEntity);
        _actionsSystem.RemoveAction(uid, component.StealthActionEntity);
        _actionsSystem.RemoveAction(uid, component.HallucinationsActionEntity);

        var stealth = EnsureComp<StealthComponent>(uid);
        _stealthSystem.SetEnabled(uid, false, stealth);
    }
}
using Robust.Shared.GameStates;
using Robust.Shared.Prototypes;

namespace Content.Shared.Gandon.Components;

[RegisterComponent, NetworkedComponent]
public sealed partial class GandonComponent : Component
{
    [DataField]
    public float EuthanasiaSleepRadius = 3f;

    [DataField]
    public float EuthanasiaSleepDuration = 9f;

    [DataField]
    public float StandoffAreaRadius = 4f;

    [DataField]
    public float StandoffThrowSpeed = 32f;

    [DataField]
    public float StandoffKnockdownDuration = 6f;

    [DataField]
    public float StandoffStunDuration = 3f;

    [DataField]
    public float HallucinationsRadius = 10f;

    [DataField]
    public float HallucinationDuration = 9f;

    [DataField]
    public float HallucinationKnockdownDuration = 8f;

    [DataField]
    public float HallucinationStunDuration = 1f;

    [DataField]
    public float StealthCooldown = 3;

    [DataField]
    public float RevealedStealthCooldown = 10;

    [DataField]
    public bool StealthToggled;

    [DataField(required: true)]
    public EntProtoId EuthanasiaActionPrototype = "ActionGandonEuthanasia";

    [DataField(required: true)]
    public EntProtoId StandoffActionPrototype = "ActionGandonStandoff";

    [DataField(required: true)]
    public EntProtoId StealthActionPrototype = "ActionGandonStealth";

    [DataField(required: true)]
    public EntProtoId HallucinationsActionPrototype = "ActionGandonHallucinations";

    [DataField]
    public EntityUid? EuthanasiaActionEntity;

    [DataField]
    public EntityUid? StandoffActionEntity;

    [DataField]
    public EntityUid? StealthActionEntity;

    [DataField]
    public EntityUid? HallucinationsActionEntity;
}

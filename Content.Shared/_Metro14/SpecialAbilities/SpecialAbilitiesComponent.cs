using Content.Shared.Actions;
using Content.Shared.Actions.Components;
using Robust.Shared.GameStates;
using Robust.Shared.Prototypes;

namespace Content.Shared._Metro14.SpecialAbilities;

[RegisterComponent, NetworkedComponent, AutoGenerateComponentState]
public sealed partial class SpecialAbilitiesComponent : Component
{
    /// <summary>
    /// Прототип действия для усыпления сущностей в радиусе
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntProtoId<InstantActionComponent> SleepAction = "ActionSpecialSleep";

    /// <summary>
    /// Прототип действия для отбрасывания сущностей в радиусе
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntProtoId<InstantActionComponent> KnockbackAction = "ActionSpecialKnockback";

    /// <summary>
    /// Прототип действия для наложения шейдера галлюцинаций
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntProtoId<InstantActionComponent> ShaderAction = "ActionSpecialShader";

    /// <summary>
    /// Прототип действия для переключения невидимости
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntProtoId<InstantActionComponent> InvisibilityAction = "ActionSpecialInvisibility";


    /// <summary>
    /// Сущность действия сна, созданная из прототипа
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntityUid? SleepActionEntity;

    /// <summary>
    /// Сущность действия отбрасывания, созданная из прототипа
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntityUid? KnockbackActionEntity;

    /// <summary>
    /// Сущность действия шейдера, созданная из прототипа
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntityUid? ShaderActionEntity;

    /// <summary>
    /// Сущность действия невидимости, созданная из прототипа
    /// </summary>
    [DataField, AutoNetworkedField]
    public EntityUid? InvisibilityActionEntity;


    /// <summary>
    /// Радиус действия способности сна в тайлах
    /// Все сущности в этом радиусе будут усыплены
    /// </summary>
    [DataField]
    public float SleepRadius = 2f;

    /// <summary>
    /// Длительность эффекта сна
    /// Сущности будут спать указанное время
    /// </summary>
    [DataField]
    public TimeSpan SleepDuration = TimeSpan.FromSeconds(3);


    /// <summary>
    /// Радиус действия способности отбрасывания в тайлах
    /// Все сущности в этом радиусе будут отброшены
    /// </summary>
    [DataField]
    public float KnockbackRadius = 6f;

    /// <summary>
    /// Сила отбрасывания
    /// Чем выше значение, тем сильнее сущности отбрасываются от пользователя
    /// </summary>
    [DataField]
    public float KnockbackForce = 20f;


    /// <summary>
    /// Радиус действия способности шейдера в тайлах
    /// Все игроки в этом радиусе увидят эффект галлюцинаций
    /// </summary>
    [DataField]
    public float ShaderRadius = 15f;

    /// <summary>
    /// Длительность эффекта шейдера
    /// Эффект галлюцинаций будет действовать указанное время
    /// </summary>
    [DataField]
    public TimeSpan ShaderDuration = TimeSpan.FromSeconds(10);
}
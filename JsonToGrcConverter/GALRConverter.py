from .Common import (
    CheckForNotImplementedConditionHandling,
    ConvertComment,
    ConvertIconId,
    ConvertToEscapedString,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)

def ConvertGALR (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    iconId = ConvertIconId (resource.pop ('iconId'))
    name = ConvertToEscapedString (resource.pop ('name', None))
    largeText = ConvertToEscapedString (resource.pop ('largeText'))
    smallText = ConvertToEscapedString (resource.pop ('smallText'))
    acceptButtonText = ConvertToEscapedString (resource.pop ('acceptButtonText'))
    cancelButtonText = ConvertToEscapedString (resource.pop ('cancelButtonText'))
    thirdButtonText = ConvertToEscapedString (resource.pop ('thirdButtonText'))

    CheckForNotImplementedConditionHandling (largeText)
    CheckForNotImplementedConditionHandling (smallText)
    CheckForNotImplementedConditionHandling (acceptButtonText)
    CheckForNotImplementedConditionHandling (cancelButtonText)
    CheckForNotImplementedConditionHandling (thirdButtonText)

    comment = ConvertComment (resource)

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    outputBuilder.AddLine (f'\'GALR\' {resId} {iconId} {name} {{{comment}')
    outputBuilder.AddLine (f'    /* largeText   */ {largeText}')
    outputBuilder.AddLine (f'    /* smallText   */ {smallText}')
    outputBuilder.AddLine (f'    /* button1     */ {acceptButtonText}')
    outputBuilder.AddLine (f'    /* button2     */ {cancelButtonText}')
    outputBuilder.AddLine (f'    /* button3     */ {thirdButtonText}')
    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())

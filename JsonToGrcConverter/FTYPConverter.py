from .Common import (
    ConvertComment,
    ConvertIconId,
    ConvertToEscapedString,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)


def ConvertFTYP (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    mimeType = ConvertToEscapedString (resource.pop ('mimeType'))
    description = ConvertToEscapedString (resource.pop ('description'))
    fileExt = ConvertToEscapedString (resource.pop ("fileExtension"))
    creator = ConvertToEscapedString (resource.pop ("creator"))
    fileType = ConvertToEscapedString (resource.pop ("type"))
    iconId = ConvertIconId (resource.pop ("iconId"))
    if iconId == 'NoIcon':
        iconId = '-1'

    comment = ConvertComment (resource)

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    outputBuilder.AddLine (f"'FTYP' {resId} {mimeType} {{{comment}")
    outputBuilder.AddLine (f"    /* description */ {description}")
    outputBuilder.AddLine (f"    /* fileExt     */ {fileExt}")
    outputBuilder.AddLine (f"    /* creator     */ {creator}")
    outputBuilder.AddLine (f"    /* type        */ {fileType}")
    outputBuilder.AddLine (f"    /* iconId      */ {iconId}")
    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())

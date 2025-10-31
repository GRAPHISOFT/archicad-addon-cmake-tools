from .Common import (
    CheckIfAllKeysWereHandled,
    ConvertComment,
    ConvertToEscapedString,
    EscapeString,
    FormatCommentLeadingSpace,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)

def ConvertFTGP (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    mime = EscapeString (resource.pop ('mime'))
    description = ConvertToEscapedString (resource.pop ('description'))

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    outputBuilder.AddLine (f'\'FTGP\' {resId} {mime} {{')
    outputBuilder.AddLine (f'    /* description */ {description}')
    outputBuilder.AddLine ('    {')
    for item in resource.pop ('group1'):
        mimeId = item.pop ('mimeId')
        mimeType = FormatCommentLeadingSpace (EscapeString (item.pop ('mimeType')))
        itemComment = ConvertComment (item)
        outputBuilder.AddLine (f'        {mimeId}{mimeType}{itemComment}')
        CheckIfAllKeysWereHandled (item)
    outputBuilder.AddLine ('    }')
    outputBuilder.AddLine ('    {')
    for item in resource.pop ('group2'):
        mimeId = item.pop ('mimeId')
        mimeType = FormatCommentLeadingSpace (EscapeString (item.pop ('mimeType')))
        itemComment = ConvertComment (item)
        outputBuilder.AddLine (f'        {mimeId}{mimeType}{itemComment}')
        CheckIfAllKeysWereHandled (item)
    outputBuilder.AddLine ('    }')
    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())

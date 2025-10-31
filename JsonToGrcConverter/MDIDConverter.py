from .Common import (
    ConvertToEscapedString,
    GrcOutputBuilder,
    ConvertComment,
    GetConditionAsIfDef,
    GetConditionEnd,
)


def ConvertMDID (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))
    value1 = resource.pop ("value1")
    value2 = resource.pop ("value2")
    assert isinstance (value1, str)
    assert isinstance (value2, str)
    comment = ConvertComment (resource)

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))

    outputBuilder.AddLine (f"'MDID' {resId} {name} {{{comment}")
    outputBuilder.AddLine (f"    {value1}")
    outputBuilder.AddLine (f"    {value2}")
    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())
from .Common import (
    ConvertComment,
    ConvertToEscapedString,
    GetConditionAsIfDef,
    GetConditionEnd,
    GrcOutputBuilder,
)


def ConvertDATA (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))
    fileName = resource.pop ('fileName', None)
    data = resource.pop ("data", None)
    comment = ConvertComment (resource)

    condition = resource.pop ('#condition', None)
    if condition:
        outputBuilder.AddLine (GetConditionAsIfDef (condition))
    
    outputBuilder.AddLine (f"'DATA' {resId} {name} {{{comment}")
    if data:
        assert not fileName, f"fileName must be empty but is: '{fileName}'"
        outputBuilder.AddLine (f"    {data}")
    elif fileName:
        assert not data, f"data must be empty but is: '{data}'"
        outputBuilder.AddLine (f"    {ConvertToEscapedString (fileName)}")
    else:
        raise RuntimeError ("DATA resource must have either fileName or data.")

    outputBuilder.AddLine ('}')

    if condition:
        outputBuilder.AddLine (GetConditionEnd ())

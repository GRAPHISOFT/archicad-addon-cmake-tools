from .Common import (
    CheckForNotImplementedConditionHandling,
    CheckIfAllKeysWereHandled,
    ConvertToEscapedString,
    GrcOutputBuilder,
)

def ConvertGCSR (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    CheckForNotImplementedConditionHandling (resource)
    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))
    hotspot = resource.pop ('hotspot')
    x = hotspot.pop ('x')
    y = hotspot.pop ('y')
    CheckIfAllKeysWereHandled (hotspot)
    outputBuilder.AddLine (f'\'GCSR\' {resId} {name} {{')
    outputBuilder.AddLine (f"    {x:>4} {y:>4}")
    outputBuilder.AddLine ('}')

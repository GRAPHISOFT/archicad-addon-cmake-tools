from .Common import (
    CheckForNotImplementedConditionHandling,
    ConvertToEscapedString,
    GrcOutputBuilder,
)


def ConvertACNF (outputBuilder: GrcOutputBuilder, resource: dict, targetAcVersion: int) -> None:
    CheckForNotImplementedConditionHandling (resource)

    resId = resource.pop ('#id')
    name = ConvertToEscapedString (resource.pop ('name'))
    version = resource.pop ('version')
    platform = resource.pop ('platform')
    flag = resource.pop ('flag')
    method = resource.pop ('method')
    subMethod = resource.pop ('subMethod')
    methodVersion = resource.pop ('methodVersion')
    methodIndex = resource.pop ('methodIndex')
    function = resource.pop ('function')
    modulName = ConvertToEscapedString (resource.pop ('modulName'))

    outputBuilder.AddLine (f'\'ACNF\' {resId} {name} {{')
    outputBuilder.AddLine (f'    {version}')
    outputBuilder.AddLine (f'    {platform}')
    outputBuilder.AddLine (f'    {flag}')
    outputBuilder.AddLine (f'    {method}')
    outputBuilder.AddLine (f'    {subMethod}')
    outputBuilder.AddLine (f'    {methodVersion}')
    outputBuilder.AddLine (f'    {methodIndex}')
    outputBuilder.AddLine (f'    {" + ".join (function)}')
    outputBuilder.AddLine (f'    {modulName}')
    outputBuilder.AddLine ('}')

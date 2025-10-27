import unittest
import JsonToGrcConverter.JsonToGrcConverter
import JsonToGrcConverter.Common
from pathlib import Path
import subprocess
import shutil
import platform
import os
import sys

"""
By default this test only compares the converted GRC file to a reference GRC file.
If the APIDEVKIT_DIR and APIDEVKIT_VERSION environment variables are set, the test will also preprocess and run ResConv on it to see if it actually compiles using a devkit.
On Windows this requires the Developer Command Prompt (or Powershell) for VS to be used to run the tests (to find cl.exe).

Using Developer Powershell for VS:
$env:APIDEVKIT_DIR="C:/Dev/API.Development.Kit.WIN.29.3000"
$env:APIDEVKIT_VERSION="29"
py -3 -m unittest
"""
APIDEVKIT_DIR: str | None = None
APIDEVKIT_VERSION: str | None = None


TESTFILES_DIR_NAME = Path (__file__).parent / 'testfiles'


TARGET_AC_VERSIONS = [25, 26, 27, 28, 29, 30]


def PreprocessGrc (inputFile: str, outputFile: str) -> None:
    if platform.system () == 'Windows':
        args = [
            'cl.exe',
            '/nologo',
            '/X',
            '/EP',
            '/P',
            '/I',
            f'{APIDEVKIT_DIR}/Support/Inc',
            '/I',
            f'{APIDEVKIT_DIR}/Support/Modules/DGLib',
            '/DWINDOWS',
            '/source-charset:utf-8',
            '/execution-charset:utf-8',
            f'/Fi{outputFile}',
            inputFile,
        ]
    else: 
        args = [
            'clang',
            '-x', 'c++',
            '-E',
            '-P',
            '-Dmacintosh',
            '-I', f'{APIDEVKIT_DIR}/Support/Inc',
            '-I', f'{APIDEVKIT_DIR}/Support/Modules/DGLib',
            '-o', outputFile,
            inputFile
        ]
    subprocess.run (args, check=True)


def RunResConv (inputFile: str, outputFile: str, includePath: str, targetAcVersion: int) -> None:
    if platform.system () == 'Windows':
        resConvPath = Path (APIDEVKIT_DIR) / 'Support' / 'Tools' / 'Win' / 'ResConv.exe'
        platformSign = 'W'
        codePage = '1252'
    else:
        resConvPath = Path (APIDEVKIT_DIR) / 'Support' / 'Tools' / 'OSX' / 'ResConv'
        platformSign = 'M'
        codePage = 'utf16'

    args = [
        str (resConvPath),
        '-m', 'r',
        '-T', platformSign,
        '-q', 'utf8', codePage,
        '-w', '2',
        '-p', includePath,
        '-i', inputFile,
        '-o', outputFile,
    ]

    if targetAcVersion >= 29:
        args.extend (['-py', sys.executable])
        args.extend (['-sc', resConvPath.parent / 'SVGColorChange.py'])

    subprocess.run (args, check=True)


class TestJsonToGrcConverter (unittest.TestCase):

    def setUp (self):
        if 'APIDEVKIT_DIR' in os.environ and 'APIDEVKIT_VERSION' in os.environ:
            global APIDEVKIT_DIR
            APIDEVKIT_DIR = os.environ['APIDEVKIT_DIR']
            global APIDEVKIT_VERSION
            APIDEVKIT_VERSION = os.environ['APIDEVKIT_VERSION']
            assert Path (APIDEVKIT_DIR).is_dir (), f'APIDEVKIT_DIR environment variable is not set to a valid directory: "{APIDEVKIT_DIR}"'
        
        self.tempDirectory = Path (__file__).parent / 'TEMP_TEST_OUTPUT'
        self.tempDirectory.mkdir (parents=True, exist_ok=True)

    def tearDown (self):
        deleteActualFiles = True
        if deleteActualFiles:
            shutil.rmtree (self.tempDirectory)

    def RunTestCase_SingleVersion (self, inputJson: Path, referenceGrc: Path, targetAcVersion: int) -> None:
        actualGrcString = JsonToGrcConverter.JsonToGrcConverter.ConvertJsonFileToGrcString (inputJson, targetAcVersion)

        referenceGrcPath = Path (referenceGrc)
        with open (referenceGrcPath, 'r', encoding='utf-8', errors='strict') as file:
            referenceGrcFileContent = file.read ()

        actualGrcOutputPath = self.tempDirectory / referenceGrcPath.name
        actualGrcOutputPath = actualGrcOutputPath.with_suffix ('.grc')

        with open (actualGrcOutputPath, 'w', encoding='utf-8', errors='strict') as file:
            file.write (actualGrcString)

        # To update the reference files, uncomment the following line:
        # shutil.copy (actualGrcOutputPath, referenceGrc)

        self.assertEqual (actualGrcString, referenceGrcFileContent, f'Actual and references files do not match.\nActual:    {actualGrcOutputPath}\nReference: {referenceGrcPath}\nModify the tearDown method to keep the actual files.')

        if APIDEVKIT_DIR is not None and int (APIDEVKIT_VERSION) == targetAcVersion:
            preprocessedGrc = actualGrcOutputPath.with_suffix ('.preprocessed')
            PreprocessGrc (str (actualGrcOutputPath), str (preprocessedGrc))

            nativeResource = actualGrcOutputPath.with_suffix ('.rc2')
            includePath = Path (referenceGrcPath).parent
            RunResConv (str (preprocessedGrc), str (nativeResource), str (includePath), targetAcVersion)

    def RunTestCase (self, inputJson: Path, referenceGrc: Path) -> None:
        for targetAcVersion in TARGET_AC_VERSIONS:
            self.RunTestCase_SingleVersion (inputJson, referenceGrc, targetAcVersion)

    def RunTestCase_VersionDependentReference (self, inputJson: Path, referenceGrc: Path) -> None:
        for targetAcVersion in TARGET_AC_VERSIONS:
            referenceGrcFileName = f'{referenceGrc.stem}_{targetAcVersion}{referenceGrc.suffix}'
            self.RunTestCase_SingleVersion (inputJson, referenceGrc.parent / referenceGrcFileName, targetAcVersion)

    def test_conditions (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'conditions.json', TESTFILES_DIR_NAME / 'conditions.grc')

    def test_special_characters (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'special_characters.json', TESTFILES_DIR_NAME / 'special_characters.grc')

    def test_unhandled_property (self):
        self.assertRaises (JsonToGrcConverter.Common.UnhandledJsonPropertyError, self.RunTestCase, TESTFILES_DIR_NAME / 'unhandled_property.json', TESTFILES_DIR_NAME / 'unhandled_property.grc')

    def test_unsupported_property_value (self):
        self.assertRaises (JsonToGrcConverter.Common.UnsupportedGDLGControlPropertyError, self.RunTestCase, TESTFILES_DIR_NAME / 'unsupported_property_value.json', TESTFILES_DIR_NAME / 'unsupported_property_value.grc')

    def test_unsupported_GDLG_control (self):
        self.assertRaises (JsonToGrcConverter.Common.UnsupportedGDLGControlError, self.RunTestCase, TESTFILES_DIR_NAME / 'unsupported_GDLG_control.json', TESTFILES_DIR_NAME / 'unsupported_GDLG_control.grc')

    def test_unsupported_resource_type (self):
        self.assertRaises (JsonToGrcConverter.Common.UnsupportedResourceTypeError, self.RunTestCase, TESTFILES_DIR_NAME / 'unsupported_resource_type.json', TESTFILES_DIR_NAME / 'unsupported_resource_type.grc')

    def test_ACNF (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'ACNF.json', TESTFILES_DIR_NAME / 'ACNF.grc')

    def test_ACP0 (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'ACP0.json', TESTFILES_DIR_NAME / 'ACP0.grc')

    def test_STRS (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'STRS.json', TESTFILES_DIR_NAME / 'STRS.grc')

    def test_CMND (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'CMND.json', TESTFILES_DIR_NAME / 'CMND.grc')

    def test_DATA (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'DATA.json', TESTFILES_DIR_NAME / 'DATA.grc')

    def test_GALR (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GALR.json', TESTFILES_DIR_NAME / 'GALR.grc')
 
    def test_DHLP (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'DHLP.json', TESTFILES_DIR_NAME / 'DHLP.grc')

    def test_FILE (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'FILE.json', TESTFILES_DIR_NAME / 'FILE.grc')

    def test_FTGP_FTYP (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'FTGP_FTYP.json', TESTFILES_DIR_NAME / 'FTGP_FTYP.grc')

    def test_GCSR (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GCSR.json', TESTFILES_DIR_NAME / 'GCSR.grc')

    def test_GICN (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GICN.json', TESTFILES_DIR_NAME / 'GICN.grc')

    def test_MDID (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'MDID.json', TESTFILES_DIR_NAME / 'MDID.grc')

    def test_TEXT (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'TEXT.json', TESTFILES_DIR_NAME / 'TEXT.grc')

    def test_macroDictionary (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'macroDictionary.json', TESTFILES_DIR_NAME / 'macroDictionary.grc')

    def test_GDLG (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG.json', TESTFILES_DIR_NAME / 'GDLG.grc')

    def test_GDLG_Button (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_Button.json', TESTFILES_DIR_NAME / 'GDLG_Button.grc')

    def test_GDLG_StaticText (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_StaticText.json', TESTFILES_DIR_NAME / 'GDLG_StaticText.grc')

    def test_GDLG_IntEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_IntEdit.json', TESTFILES_DIR_NAME / 'GDLG_IntEdit.grc')

    def test_GDLG_Popup (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Popup.json', TESTFILES_DIR_NAME / 'GDLG_Popup.grc')

    def test_GDLG_CheckBox (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_CheckBox.json', TESTFILES_DIR_NAME / 'GDLG_CheckBox.grc')

    def test_GDLG_Browser (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Browser.json', TESTFILES_DIR_NAME / 'GDLG_Browser.grc')

    def test_GDLG_Date (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Date.json', TESTFILES_DIR_NAME / 'GDLG_Date.grc')

    def test_GDLG_GroupBox (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_GroupBox.json', TESTFILES_DIR_NAME / 'GDLG_GroupBox.grc')

    def test_GDLG_Icon (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Icon.json', TESTFILES_DIR_NAME / 'GDLG_Icon.grc')

    def test_GDLG_IconButton (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_IconButton.json', TESTFILES_DIR_NAME / 'GDLG_IconButton.grc')

    def test_GDLG_IconCheckBox (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_IconCheckBox.json', TESTFILES_DIR_NAME / 'GDLG_IconCheckBox.grc')

    def test_GDLG_IconMenuCheck (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_IconMenuCheck.json', TESTFILES_DIR_NAME / 'GDLG_IconMenuCheck.grc')

    def test_GDLG_IconMenuRadio (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_IconMenuRadio.json', TESTFILES_DIR_NAME / 'GDLG_IconMenuRadio.grc')

    def test_GDLG_IconPushCheck (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_IconPushCheck.json', TESTFILES_DIR_NAME / 'GDLG_IconPushCheck.grc')

    def test_GDLG_IconRadioButton (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_IconRadioButton.json', TESTFILES_DIR_NAME / 'GDLG_IconRadioButton.grc')

    def test_GDLG_LengthEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_LengthEdit.json', TESTFILES_DIR_NAME / 'GDLG_LengthEdit.grc')

    def test_GDLG_ListBox (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_ListBox.json', TESTFILES_DIR_NAME / 'GDLG_ListBox.grc')

    def test_GDLG_ListView (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_ListView.json', TESTFILES_DIR_NAME / 'GDLG_ListView.grc')

    def test_GDLG_MultiLineEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_MultiLineEdit.json', TESTFILES_DIR_NAME / 'GDLG_MultiLineEdit.grc')

    def test_GDLG_NormalTab (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_NormalTab.json', TESTFILES_DIR_NAME / 'GDLG_NormalTab.grc')

    def test_GDLG_ProgressBar (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_ProgressBar.json', TESTFILES_DIR_NAME / 'GDLG_ProgressBar.grc')

    def test_GDLG_PushCheck (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_PushCheck.json', TESTFILES_DIR_NAME / 'GDLG_PushCheck.grc')

    def test_GDLG_RadioButton (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_RadioButton.json', TESTFILES_DIR_NAME / 'GDLG_RadioButton.grc')

    def test_GDLG_RichEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_RichEdit.json', TESTFILES_DIR_NAME / 'GDLG_RichEdit.grc')

    def test_GDLG_Ruler (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Ruler.json', TESTFILES_DIR_NAME / 'GDLG_Ruler.grc')

    def test_GDLG_SAMQuantityEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_SAMQuantityEdit.json', TESTFILES_DIR_NAME / 'GDLG_SAMQuantityEdit.grc')

    def test_GDLG_ScrollBar (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_ScrollBar.json', TESTFILES_DIR_NAME / 'GDLG_ScrollBar.grc')

    def test_GDLG_Separator (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Separator.json', TESTFILES_DIR_NAME / 'GDLG_Separator.grc')

    def test_GDLG_SimpleTab (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_SimpleTab.json', TESTFILES_DIR_NAME / 'GDLG_SimpleTab.grc')

    def test_GDLG_Slider (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Slider.json', TESTFILES_DIR_NAME / 'GDLG_Slider.grc')

    def test_GDLG_SpinControl (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_SpinControl.json', TESTFILES_DIR_NAME / 'GDLG_SpinControl.grc')

    def test_GDLG_SplitButton (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_SplitButton.json', TESTFILES_DIR_NAME / 'GDLG_SplitButton.grc')

    def test_GDLG_Splitter (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Splitter.json', TESTFILES_DIR_NAME / 'GDLG_Splitter.grc')

    def test_GDLG_TabBar (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_TabBar.json', TESTFILES_DIR_NAME / 'GDLG_TabBar.grc')

    def test_GDLG_TextEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_TextEdit.json', TESTFILES_DIR_NAME / 'GDLG_TextEdit.grc')

    def test_GDLG_Time (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_Time.json', TESTFILES_DIR_NAME / 'GDLG_Time.grc')

    def test_GDLG_TreeView (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_TreeView.json', TESTFILES_DIR_NAME / 'GDLG_TreeView.grc')

    def test_GDLG_UniRichEdit (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_UniRichEdit.json', TESTFILES_DIR_NAME / 'GDLG_UniRichEdit.grc')

    def test_GDLG_UserControl (self):
        self.RunTestCase_VersionDependentReference (TESTFILES_DIR_NAME / 'GDLG_UserControl.json', TESTFILES_DIR_NAME / 'GDLG_UserControl.grc')

    def test_GDLG_UserItem (self):
        self.RunTestCase (TESTFILES_DIR_NAME / 'GDLG_UserItem.json', TESTFILES_DIR_NAME / 'GDLG_UserItem.grc')

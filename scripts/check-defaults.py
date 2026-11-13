# Run with the office's bundled Python against a running soffice (see scripts/build-macos.sh step "defaults").
# Usage: python check-defaults.py <pipe> en   -> fresh profile: config/1x-defaults.xcd took effect, English UI
#        python check-defaults.py <pipe> vi   -> profile switched to Vietnamese: the 1x translations reach the office
import sys
import time

import uno
from com.sun.star.beans import PropertyValue

EXPECTED = [
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Writer", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Calc", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Impress", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Draw", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.Linguistic/General", "UILocale", "en-US"),
    ("/org.openoffice.Setup/Office/Factories/com.sun.star.text.TextDocument", "ooSetupFactoryDefaultFilter", "MS Word 2007 XML"),
    ("/org.openoffice.Setup/Office/Factories/com.sun.star.sheet.SpreadsheetDocument", "ooSetupFactoryDefaultFilter", "Calc MS Excel 2007 XML"),
    ("/org.openoffice.Setup/Office/Factories/com.sun.star.presentation.PresentationDocument", "ooSetupFactoryDefaultFilter", "Impress MS PowerPoint 2007 XML"),
    ("/org.openoffice.Office.Common/Save/Document", "WarnAlienFormat", False),
    ("/org.openoffice.Office.Common/Security/Scripting", "MacroSecurityLevel", 2),
    ("/org.openoffice.Setup/Product", "WhatsNew", False),
    ("/org.openoffice.Office.Common/Misc", "ShowTipOfTheDay", False),
    ("/org.openoffice.Setup/Product", "LastTimeGetInvolvedShown", 32503680000),
    ("/org.openoffice.Setup/Product", "LastTimeDonateShown", 32503680000),
    ("/org.openoffice.Setup/Product", "ooName", "1xVnOffice"),
    ("/org.openoffice.Office.UI/ColorScheme", "CurrentColorScheme", "1xVnOffice"),
    ("/org.openoffice.Office.UI/ColorScheme/ColorSchemes/1xVnOffice/AccentColor", "Color", 0x4C7DFF),
    ("/org.openoffice.Office.Common/Appearance", "LibreOfficeTheme", 1),
    ("/org.openoffice.Office.Common/Misc", "SymbolStyle", "1x"),
    ("/org.openoffice.Office.Common/Misc", "ShowDonation", False),
    ("/org.openoffice.Office.Impress/Misc/NewDoc", "AutoPilot", False),
    ("/org.openoffice.Office.Common/Menus", "CreditsURL", "https://xuanhieu.org"),
    ("/org.openoffice.Office.Common/Menus", "ReleaseNotesURL", "https://github.com/xuanhieu/1xvnoffice/releases"),
    ("/org.openoffice.Office.Common/Menus", "SendFeedbackURL", "https://github.com/xuanhieu/1xvnoffice/issues"),
    ("/org.openoffice.Office.Common/Help/StartCenter", "InfoURL", "https://1xag.com"),
]


def connect(pipe):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(60):
        try:
            return resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
        except Exception:  # noqa: BLE001 - office still starting
            time.sleep(1)
    sys.exit("không kết nối được tới soffice")


CUT_LABEL = {"en": "~Cut", "vi": "~Cắt"}


def main():
    ctx = connect(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    provider = ctx.ServiceManager.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
    failures = 0
    for path, prop, want in (EXPECTED if lang == "en" else []):
        arg = PropertyValue()
        arg.Name, arg.Value = "nodepath", path
        node = provider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
        got = node.getPropertyValue(prop)
        ok = got == want
        failures += not ok
        print(f"{'OK  ' if ok else 'SAI '} {path}/{prop} = {got!r}" + ("" if ok else f" (mong đợi {want!r})"))
    # The label of Cut, read from the running office, proves which UI language and config translations are active.
    commands = ctx.getValueByName("/singletons/com.sun.star.frame.theUICommandDescription")
    label = dict((p.Name, p.Value) for p in commands.getByName("com.sun.star.text.TextDocument").getByName(".uno:Cut"))["Label"]
    want = CUT_LABEL[lang]
    ok = label == want
    failures += not ok
    print(f"{'OK  ' if ok else 'SAI '} nhãn ({lang}) của .uno:Cut = {label!r}" + ("" if ok else f" (mong đợi {want!r})"))
    try:
        ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx).terminate()
    except Exception:  # noqa: BLE001 - the bridge drops when the office exits
        pass
    sys.exit(1 if failures else 0)


main()

# Run with the office's bundled Python against a running soffice (see scripts/build-macos.sh step "defaults").
# Reads the effective configuration of a fresh profile and checks that config/1x-defaults.xcd took effect.
import sys
import time

import uno
from com.sun.star.beans import PropertyValue

EXPECTED = [
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Writer", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Calc", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Impress", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.UI.ToolbarMode/Applications/Draw", "Active", "notebookbar.ui"),
    ("/org.openoffice.Office.Linguistic/General", "UILocale", "vi"),
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


def main():
    ctx = connect(sys.argv[1])
    provider = ctx.ServiceManager.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", ctx)
    failures = 0
    for path, prop, want in EXPECTED:
        arg = PropertyValue()
        arg.Name, arg.Value = "nodepath", path
        node = provider.createInstanceWithArguments("com.sun.star.configuration.ConfigurationAccess", (arg,))
        got = node.getPropertyValue(prop)
        ok = got == want
        failures += not ok
        print(f"{'OK  ' if ok else 'SAI '} {path}/{prop} = {got!r}" + ("" if ok else f" (mong đợi {want!r})"))
    # Translations must reach the running office: the ribbon label of Cut comes from the Vietnamese config layer.
    commands = ctx.getValueByName("/singletons/com.sun.star.frame.theUICommandDescription")
    label = dict((p.Name, p.Value) for p in commands.getByName("com.sun.star.text.TextDocument").getByName(".uno:Cut"))["Label"]
    ok = label == "~Cắt"
    failures += not ok
    print(f"{'OK  ' if ok else 'SAI '} nhãn tiếng Việt của .uno:Cut = {label!r}" + ("" if ok else " (mong đợi '~Cắt')"))
    try:
        ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx).terminate()
    except Exception:  # noqa: BLE001 - the bridge drops when the office exits
        pass
    sys.exit(1 if failures else 0)


main()

import os
import sys
import threading
import uno
from com.sun.star.beans import PropertyValue

# Append the system LibreOffice python path so the Conda env can import 'uno'
sys.path.append('/usr/lib/python3/dist-packages')

# Lock to prevent concurrent UNO calls from crashing LibreOffice
lo_lock = threading.Lock()

def convert_to_pdf(input_path: str, output_path: str) -> bool:
    """Opens a document via UNO, applies formatting, and exports to PDF."""
    with lo_lock:
        localContext = uno.getComponentContext()
        resolver = localContext.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", localContext)

        try:
            ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
        except Exception as e:
            print(f"Failed to connect to LibreOffice server: {e}")
            return False

        smgr = ctx.ServiceManager
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

        input_url = uno.systemPathToFileUrl(os.path.abspath(input_path))
        load_props = (
            PropertyValue(Name="Hidden", Value=True),
            PropertyValue(Name="ReadOnly", Value=False)
        )

        try:
            doc = desktop.loadComponentFromURL(input_url, "_blank", 0, load_props)
        except Exception as e:
            print(f"Error loading {os.path.basename(input_path)}: {e}")
            return False

        if not doc:
            return False

        filter_name = "writer_pdf_Export" # Default fallback

        # --- FIX PAGINATION AND MARGINS FOR EXCEL/CALC ---
        if doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
            style_families = doc.StyleFamilies
            if style_families.hasByName("PageStyles"):
                page_styles = style_families.getByName("PageStyles")
                for i in range(page_styles.getCount()):
                    style = page_styles.getByIndex(i)
                    style.ScaleToPagesX = 1
                    style.ScaleToPagesY = 0
                    style.LeftMargin = int(style.LeftMargin * 0.25)
                    style.RightMargin = int(style.RightMargin * 0.25)
                    style.TopMargin = int(style.TopMargin * 0.25)
                    style.BottomMargin = int(style.BottomMargin * 0.25)
            filter_name = "calc_pdf_Export"

        elif doc.supportsService("com.sun.star.presentation.PresentationDocument"):
            filter_name = "impress_pdf_Export"

        output_url = uno.systemPathToFileUrl(os.path.abspath(output_path))
        save_props = (PropertyValue(Name="FilterName", Value=filter_name),)

        success = False
        try:
            doc.storeToURL(output_url, save_props)
            success = True
        except Exception as e:
            print(f"Error saving PDF: {e}")
        finally:
            try:
                doc.close(True)
            except:
                pass

        return success
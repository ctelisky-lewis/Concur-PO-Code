import azure.functions as func
import logging
from . import concur_po_logic  # Import your logic file

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="ConcurPOFileBuilder")
def ConcurPOFileBuilder(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Concur PO Builder function triggered.')

    try:
        concur_po_logic.main()   # <-- run your existing logic
        return func.HttpResponse(
            "Concur PO file build completed successfully.",
            status_code=200
        )
    except Exception as e:
        logging.exception("Error running Concur PO Builder.")
        return func.HttpResponse(str(e), status_code=500)

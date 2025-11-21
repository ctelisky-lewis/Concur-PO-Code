import logging
import azure.functions as func
import concur_po_logic

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Concur PO Builder HTTP trigger started.")

    try:
        concur_po_logic.main()
        return func.HttpResponse(
            "Concur PO file build completed successfully.",
            status_code=200
        )
    except Exception as e:
        logging.exception("Error running Concur PO Builder.")
        return func.HttpResponse(str(e), status_code=500)

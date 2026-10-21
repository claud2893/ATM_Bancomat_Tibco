from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent
XML_PATH = ROOT / 'XMLprelievi' / 'prelievo.xml'
RECEIPT_PATH = ROOT / 'Ricevuta' / 'ricevuta.txt'
XML_NAMESPACE = 'http://www.example.org/prelievo'
FIELD_NAMES = ('nome', 'cognome', 'pin', 'importo_operazione')
QUALIFIED_FIELD_NAMES = tuple(f'{{{XML_NAMESPACE}}}{name}' for name in FIELD_NAMES)
INVALID_CHARACTERS = frozenset(r"""\?!/+*=‘’“”'";,-.^&%$(){}[]""")
ET.register_namespace('', XML_NAMESPACE)


class ATMRequestHandler(BaseHTTPRequestHandler):
    def send_text(self, status, text, content_type='text/plain; charset=utf-8'):
        body = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/ricevuta':
            self.get_receipt()
            return

        resource = {
            '/': ('index.html', 'text/html; charset=utf-8'),
            '/index.html': ('index.html', 'text/html; charset=utf-8'),
            '/script.js': ('script.js', 'text/javascript; charset=utf-8'),
            '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
        }.get(self.path)

        if resource is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        filename, content_type = resource
        body = (ROOT / filename).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def get_receipt(self):
        try:
            receipt = RECEIPT_PATH.read_bytes().decode('utf-8')
        except FileNotFoundError:
            self.send_text(HTTPStatus.ACCEPTED, 'Ricevuta non ancora disponibile.')
            return
        except (OSError, UnicodeError):
            self.send_text(HTTPStatus.INTERNAL_SERVER_ERROR, 'Impossibile leggere la ricevuta.')
            return

        if not receipt.strip():
            self.send_text(HTTPStatus.ACCEPTED, 'Ricevuta non ancora disponibile.')
            return

        self.send_text(HTTPStatus.OK, receipt)

    def do_POST(self):
        if self.path == '/api/nuova-operazione':
            try:
                RECEIPT_PATH.unlink(missing_ok=True)
            except OSError:
                self.send_text(HTTPStatus.INTERNAL_SERVER_ERROR, 'Impossibile eliminare la ricevuta.')
                return

            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return

        if self.path != '/api/prelievi':
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get('Content-Length', '0'))
            if content_length <= 0 or content_length > 16_384:
                raise ValueError('Dimensione richiesta non valida.')

            root = ET.fromstring(self.rfile.read(content_length))
            if root.tag != f'{{{XML_NAMESPACE}}}prelievo' or [child.tag for child in root] != list(QUALIFIED_FIELD_NAMES):
                raise ValueError('Struttura XML non valida.')

            values = {field_name: child.text or '' for field_name, child in zip(FIELD_NAMES, root)}
            if any(child.attrib or list(child) for child in root):
                raise ValueError('Struttura XML non valida.')
            if not values['nome'].strip() or not values['cognome'].strip():
                raise ValueError('Nome e cognome sono obbligatori.')
            if any(character in INVALID_CHARACTERS for value in values.values() for character in value):
                raise ValueError('La richiesta contiene caratteri non consentiti.')
            if not re.fullmatch(r'[0-9]{1,5}', values['pin']):
                raise ValueError('PIN non valido.')
            if not re.fullmatch(r'[0-9]+', values['importo_operazione']):
                raise ValueError('Importo non valido.')
            amount = int(values['importo_operazione'])
            if not 1 <= amount <= 200:
                raise ValueError('L’importo deve essere compreso tra 1 e 200 euro.')

            RECEIPT_PATH.unlink(missing_ok=True)
            XML_PATH.parent.mkdir(exist_ok=True)
            ET.indent(root, space='  ')
            xml_content = ET.tostring(root, encoding='utf-8', xml_declaration=True)
            temporary_path = XML_PATH.with_suffix('.xml.tmp')
            temporary_path.write_bytes(xml_content)
            temporary_path.replace(XML_PATH)
        except (ET.ParseError, ValueError):
            self.send_text(HTTPStatus.BAD_REQUEST, 'Richiesta non valida o impossibile da salvare.')
            return
        except OSError:
            self.send_text(HTTPStatus.INTERNAL_SERVER_ERROR, 'Impossibile salvare la richiesta o preparare la ricevuta.')
            return

        self.send_text(HTTPStatus.CREATED, 'XML salvato.')


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8000), ATMRequestHandler)
    print('ATM BANCOMAT disponibile su http://127.0.0.1:8000')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
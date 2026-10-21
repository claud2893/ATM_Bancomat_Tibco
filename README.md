# ATM Bancomat

Progetto dimostrativo per la gestione di prelievi ATM. Un'interfaccia web raccoglie i dati della richiesta, un server Python li salva in un file XML e un processo TIBCO BusinessWorks legge il file, aggiorna il saldo su PostgreSQL e restituisce l'esito all'interfaccia.

## Funzionalità

- Inserimento di nome, cognome e PIN.
- Scelta di un importo predefinito (50, 100 o 200 euro) oppure personalizzato da 1 a 200 euro.
- Validazione dei dati nel browser e nel server.
- Aggiornamento del saldo solo se il conto esiste e ha fondi sufficienti.
- Visualizzazione dell'esito restituito da TIBCO, incluso il nuovo saldo in caso di successo.

## Componenti

- `index.html`, `styles.css`, `script.js`: interfaccia, validazione e invio delle richieste.
- `server.py`: server HTTP locale, endpoint API e salvataggio della richiesta in XML.
- `XMLprelievi/prelievo.xml`: file letto dal processo TIBCO.
- `Ricevuta/ricevuta.txt`: file di esito scritto da TIBCO e letto dal server.
- `TibcoWorkspace/ATM_Bancomat`: modulo TIBCO BusinessWorks, con il processo `atm_bancomat/Prelievo`.

## Requisiti

- Python 3.9 o successivo (il server usa solo la libreria standard).
- TIBCO BusinessWorks 6.8, come indicato nel progetto.
- PostgreSQL e il driver JDBC PostgreSQL compatibile con TIBCO.

## Configurazione

### PostgreSQL

Creare il database e la tabella utilizzando, ad esempio, questo schema:

```sql
CREATE TABLE public.conti (
    id INTEGER PRIMARY KEY,
    nome VARCHAR(60) NOT NULL,
    cognome VARCHAR(60) NOT NULL,
    saldo INTEGER NOT NULL DEFAULT 0
);
```

Popolare `public.conti` con i conti da usare. Il processo confronta il PIN inserito con `id`, oltre a verificare nome e cognome; non è prevista una colonna `pin` separata.

### TIBCO BusinessWorks

Importare/aprire il workspace `TibcoWorkspace` in TIBCO BusinessStudio e configurare il modulo `ATM_Bancomat`:

1. In **Module Properties**, modificare i valori di `XMLinput` e `Ricevuta` inserendo i percorsi assoluti delle directory e dei file sul proprio ambiente. `XMLinput` deve puntare al file `XMLprelievi/prelievo.xml`; `Ricevuta` al file `Ricevuta/ricevuta.txt`. Le directory devono esistere o essere accessibili al runtime TIBCO.
2. In **JDBCConnectionResource** (`Resources/atm_bancomat/JDBCConnectionResource.jdbcResource`), impostare le proprie variabili per connessione: URL/host e porta PostgreSQL, nome del database, username e password. Verificare inoltre che il driver JDBC configurato sia disponibile nel runtime.
3. Verificare che il runtime TIBCO possa leggere il file XML e scrivere la ricevuta negli stessi percorsi configurati nel server Python.

I percorsi inclusi nel workspace sono valori locali di esempio: non usarli senza averli aggiornati per il proprio ambiente. Non inserire credenziali reali nei file versionati; utilizzare la gestione delle credenziali e delle proprietà del runtime TIBCO.

## Avvio

1. Avviare PostgreSQL e verificare la connessione configurata in TIBCO.
2. Avviare l'applicazione TIBCO BusinessWorks con il processo `Prelievo`.
3. Dalla cartella principale del progetto, avviare il server:

   ```bash
   python server.py
   ```

4. Aprire <http://127.0.0.1:8000/> nel browser.
5. Inserire i dati del conto e l'importo. Il processo TIBCO controlla la cartella delle richieste ogni 5 secondi; l'interfaccia attende la ricevuta fino a 60 secondi.

Per arrestare il server Python, usare `Ctrl+C` nel terminale in cui è in esecuzione.

## API locali

- `POST /api/prelievi`: riceve la richiesta XML, la valida e la salva in `XMLprelievi/prelievo.xml`.
- `GET /api/ricevuta`: restituisce l'esito TIBCO quando `Ricevuta/ricevuta.txt` è disponibile.
- `POST /api/nuova-operazione`: elimina la ricevuta precedente per consentire una nuova operazione.

## Sicurezza

Questo progetto è dimostrativo e non è adatto all'esposizione su Internet o all'uso con conti reali. Il PIN viene trasmesso e salvato in chiaro nel file XML per essere letto dal processo TIBCO. Prima di un utilizzo reale servono, tra le altre misure, autenticazione e protezione delle credenziali, trasporto cifrato, gestione sicura dei segreti e adeguate garanzie di concorrenza e integrità delle operazioni.

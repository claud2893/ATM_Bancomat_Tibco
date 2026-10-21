const form = document.querySelector('#withdrawal-form');
const sanitizedInputs = document.querySelectorAll('.sanitized-input');
const amountOptions = document.querySelectorAll('input[name="importo"]');
const customAmountGroup = document.querySelector('#custom-amount-group');
const customAmount = document.querySelector('#custom-amount');
const confirmationDialog = document.querySelector('#confirmation-dialog');
const confirmationMark = document.querySelector('#confirmation-mark');
const confirmationHeading = document.querySelector('#confirmation-heading');
const confirmationError = document.querySelector('#confirmation-error');
const newOperationButton = document.querySelector('#new-operation');
const submitButton = document.querySelector('#submit-button');
const formError = document.querySelector('#form-error');

const xmlNamespace = 'http://www.example.org/prelievo';
const invalidCharacters = /[\\?!\/+*=‘’“”'";,\-.^&%$(){}\[\]]/g;
const receiptPollInterval = 500;
const receiptWaitTimeout = 60_000;
const errorReceipts = new Set([
  'Combinazione nome, cognome e pin non valida.',
  'Saldo insufficiente. Impossibile effettuare il prelievo.',
]);

sanitizedInputs.forEach((input) => {
  input.addEventListener('input', () => {
    input.value = input.value.replace(invalidCharacters, '');
  });
});

amountOptions.forEach((option) => {
  option.addEventListener('change', () => {
    const customSelected = option.value === 'altro' && option.checked;
    if (customSelected) {
      customAmountGroup.hidden = false;
      customAmount.disabled = false;
      customAmount.required = true;
      customAmount.focus();
      return;
    }

    if (option.checked) {
      customAmountGroup.hidden = true;
      customAmount.disabled = true;
      customAmount.required = false;
      customAmount.value = '';
    }
  });
});

customAmount.addEventListener('input', () => {
  const value = customAmount.value;
  const amount = Number(value);
  const isIntegerAmount = /^[0-9]{1,3}$/.test(value) && amount >= 1 && amount <= 200;
  customAmount.setCustomValidity(value && !isIntegerAmount ? 'Inserisci un importo intero da 1 a 200 euro.' : '');
});

function createRequestXml() {
  const selectedAmount = form.elements.importo.value;
  const amount = selectedAmount === 'altro' ? customAmount.value : selectedAmount;
  const xmlDocument = document.implementation.createDocument(xmlNamespace, 'prelievo');
  const fields = {
    nome: form.elements.nome.value,
    cognome: form.elements.cognome.value,
    pin: form.elements.pin.value,
    importo_operazione: amount,
  };

  Object.entries(fields).forEach(([tagName, value]) => {
    const element = xmlDocument.createElementNS(xmlNamespace, tagName);
    element.textContent = value;
    xmlDocument.documentElement.append(element);
  });

  return new XMLSerializer().serializeToString(xmlDocument);
}

async function waitForReceipt() {
  const deadline = Date.now() + receiptWaitTimeout;

  while (Date.now() < deadline) {
    const response = await fetch('/api/ricevuta', { cache: 'no-store' });

    if (response.status === 202) {
      await new Promise((resolve) => window.setTimeout(resolve, receiptPollInterval));
      continue;
    }

    if (!response.ok) {
      throw new Error('Non è stato possibile leggere la ricevuta.');
    }

    const receipt = (await response.text()).trim();
    if (receipt) {
      confirmationHeading.textContent = receipt;
      newOperationButton.hidden = false;
      const isError = errorReceipts.has(receipt);
      confirmationMark.textContent = isError ? 'X' : '✓';
      confirmationMark.classList.toggle('confirmation-mark-error', isError);
      return;
    }
  }

  throw new Error('La ricevuta non è stata generata entro il tempo previsto.');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (!form.reportValidity()) {
    return;
  }

  formError.hidden = true;
  submitButton.disabled = true;

  try {
    const response = await fetch('/api/prelievi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/xml' },
      body: createRequestXml(),
    });

    if (!response.ok) {
      throw new Error('Salvataggio non riuscito.');
    }

    confirmationError.hidden = true;
    confirmationHeading.textContent = 'Elaborazione della richiesta in corso…';
    newOperationButton.hidden = true;
    confirmationDialog.showModal();

    try {
      await waitForReceipt();
    } catch (error) {
      confirmationHeading.textContent = 'Esito non disponibile';
      confirmationError.textContent = error.message;
      confirmationError.hidden = false;
      newOperationButton.hidden = false;
    }
  } catch {
    formError.textContent = 'Impossibile salvare la richiesta. Verifica che il server locale sia avviato e riprova.';
    formError.hidden = false;
  } finally {
    submitButton.disabled = false;
  }
});

newOperationButton.addEventListener('click', async () => {
  newOperationButton.disabled = true;
  confirmationError.hidden = true;

  try {
    const response = await fetch('/api/nuova-operazione', { method: 'POST' });
    if (!response.ok) {
      throw new Error('Impossibile eliminare la ricevuta. Riprova.');
    }

    window.location.reload();
  } catch (error) {
    confirmationError.textContent = error.message;
    confirmationError.hidden = false;
    newOperationButton.disabled = false;
  }
});
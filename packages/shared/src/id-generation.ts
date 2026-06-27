let admissionCounter = 0;
let receiptCounter = 0;

export function generateAdmissionNumber(): string {
  const year = new Date().getFullYear().toString().slice(-2);
  admissionCounter++;
  const seq = admissionCounter.toString().padStart(4, '0');
  return `ADM-${year}${seq}`;
}

export function generateReceiptNumber(): string {
  const year = new Date().getFullYear().toString().slice(-2);
  receiptCounter++;
  const seq = receiptCounter.toString().padStart(5, '0');
  return `RCP-${year}${seq}`;
}

export function resetAdmissionCounter(value: number = 0): void {
  admissionCounter = value;
}

export function resetReceiptCounter(value: number = 0): void {
  receiptCounter = value;
}

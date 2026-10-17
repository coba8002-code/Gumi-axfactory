export function partition(items, owner) {
  return items.filter(x => x.owner === owner).sort((a,b) => a.created - b.created);
}
export function retryable(status) {
  return status === 0 || status === 408 || status === 429 || status >= 500;
}
function open() {
  return new Promise((resolve,reject) => {
    const r = indexedDB.open("jux-autolog-v1",1);
    r.onupgradeneeded = () => r.result.createObjectStore("queue",{keyPath:"id"});
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function transact(mode, fn) {
  const db = await open();
  return new Promise((resolve,reject) => {
    const tx = db.transaction("queue",mode), request = fn(tx.objectStore("queue"));
    tx.oncomplete = () => {resolve(request.result);db.close();};
    tx.onerror = () => {reject(tx.error);db.close();};
    tx.onabort = () => {reject(tx.error);db.close();};
  });
}
export const put = item => transact("readwrite", s => s.put(item));
export const remove = id => transact("readwrite", s => s.delete(id));
export const all = () => transact("readonly", s => s.getAll());

export async function send(item, api) {
  // Stable IDs make recovery safe if the server committed before connection loss.
  await api("/incidents",{method:"POST",body:JSON.stringify(item.incident)});
  await api("/incidents/"+item.incident.id+"/actions",{method:"POST",body:JSON.stringify(item.action)});
}

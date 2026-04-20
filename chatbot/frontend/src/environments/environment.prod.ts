// wsUrl is relative to the current host — nginx proxies /ws/ to the backend.
// Empty string means "same origin", which works behind the nginx reverse proxy.
export const environment = {
  production: true,
  wsUrl: '',
  apiUrl: '',
};

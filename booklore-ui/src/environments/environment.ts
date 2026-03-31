const backendHost = window.location.hostname;

export const environment = {
  production: false,
  API_CONFIG: {
    BASE_URL: `http://${backendHost}:6060`,
    BROKER_URL: `ws://${backendHost}:6060/ws`,
  },
};

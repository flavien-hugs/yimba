import { createApi } from './client.js';
import { createSession } from './session.svelte.js';
import { browserTokenStore } from './tokens.js';

export { createApi, type Api } from './client.js';
export { ApiError, describe } from './errors.js';
export { createSession, type Session } from './session.svelte.js';
export { browserTokenStore, memoryTokenStore, type TokenStore } from './tokens.js';
export type * from './types.js';

/** The API of the backend, shared by the pages of an app. */
export const api = createApi({ store: browserTokenStore() });

/** The signed-in account. */
export const session = createSession(api);

// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
	namespace App {
		interface Error {
			/** Error code of the API, when the error comes from it. */
			code?: string;
		}
	}
}

export {};

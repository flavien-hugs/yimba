/** An answer of the API other than 2xx, or no answer at all (status 0). */
export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly code: string,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

/** Reads the error body: {code, message} from the API, {detail: [...]} from request validation. */
export async function errorFrom(response: Response): Promise<ApiError> {
	let body: unknown = null;
	try {
		body = await response.json();
	} catch {
		// not JSON (proxy error page, empty body)
	}
	if (isRecord(body) && typeof body.code === 'string') {
		return new ApiError(response.status, body.code, String(body.message ?? ''));
	}
	if (isRecord(body) && Array.isArray(body.detail)) {
		const details = body.detail.map((item) => (isRecord(item) ? String(item.msg ?? '') : '')).filter(Boolean);
		return new ApiError(response.status, 'validation', details.join('; '));
	}
	return new ApiError(response.status, `http/${response.status}`, response.statusText);
}

const MESSAGES: Record<string, string> = {
	network: 'Impossible de joindre Yimba. Vérifiez votre connexion, puis réessayez.',
	validation: 'Certaines valeurs ne sont pas acceptées. Vérifiez le formulaire.',
	'identity/invalid-credentials': 'Courriel ou mot de passe incorrect.',
	'identity/email-taken': 'Un compte existe déjà avec ce courriel.',
	'identity/invalid-email': "Cette adresse de courriel n'est pas valide.",
	'identity/registration-closed': 'Les inscriptions sont fermées. Demandez un accès à un administrateur.',
	'identity/wrong-password': "Le mot de passe actuel n'est pas le bon.",
	'identity/last-admin': 'Il doit rester au moins un administrateur actif.',
	'identity/user-not-found': "Ce compte n'existe pas ou plus.",
	'identity/forbidden': "Votre compte n'a pas accès à cette action.",
	'identity/not-admin': "Ce compte n'a pas accès à l'administration.",
	'identity/session-expired': 'Votre session a expiré. Reconnectez-vous.',
	'identity/invalid-token': 'Votre session a expiré. Reconnectez-vous.',
	'identity/missing-token': 'Connectez-vous pour continuer.',
	'watch/already-exists': 'Vous avez déjà une veille avec ce nom.',
	'watch/not-found': "Cette veille n'existe pas ou plus.",
	'alert/not-found': "Cette alerte n'existe pas ou plus."
};

/** A sentence in French for the person using the app, whatever the error. */
export function describe(error: unknown): string {
	if (!(error instanceof ApiError)) return 'Une erreur inattendue est survenue. Réessayez dans un instant.';
	if (error.code === 'identity/weak-password') {
		const [min, max] = error.message.match(/\d+/g) ?? [];
		return min && max
			? `Le mot de passe doit compter entre ${min} et ${max} caractères.`
			: "Ce mot de passe n'a pas la bonne longueur.";
	}
	if (MESSAGES[error.code]) return MESSAGES[error.code];
	if (error.status === 401) return MESSAGES['identity/session-expired'];
	if (error.status === 403) return MESSAGES['identity/forbidden'];
	if (error.status === 404) return "Ce que vous cherchez n'existe pas ou plus.";
	if (error.status === 422) return MESSAGES.validation;
	// Without a JSON body, a 502-504 comes from the proxy: the API itself does not answer.
	if (error.code.startsWith('http/') && error.status >= 502 && error.status <= 504) return MESSAGES.network;
	if (error.status === 502) return 'Un service extérieur ne répond pas. Réessayez dans un instant.';
	return 'Yimba a rencontré un problème. Réessayez dans un instant.';
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

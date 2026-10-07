import type { Emotion, Sentiment, Source } from '@yimba/api';

export const SOURCES: Record<Source, string> = {
	facebook: 'Facebook',
	instagram: 'Instagram',
	youtube: 'YouTube',
	bluesky: 'Bluesky',
	news: 'Presse en ligne',
	gdelt: 'Presse internationale'
};

export const SOURCE_ORDER: Source[] = ['facebook', 'instagram', 'youtube', 'bluesky', 'news', 'gdelt'];

export const SENTIMENTS: Record<Sentiment, { label: string; plural: string; tone: string; avatar: string }> =
	{
		negative: {
			label: 'Négatif',
			plural: 'Négatives',
			tone: 'bg-clay-soft text-clay-ink',
			avatar: 'text-clay'
		},
		neutral: {
			label: 'Neutre',
			plural: 'Neutres',
			tone: 'bg-sand-soft text-sand-ink',
			avatar: 'text-sand-ink'
		},
		positive: {
			label: 'Positif',
			plural: 'Positives',
			tone: 'bg-leaf-soft text-leaf-ink',
			avatar: 'text-leaf'
		}
	};

export const EMOTIONS: Record<Emotion, { label: string; bar: string }> = {
	fear: { label: 'Peur', bar: 'bg-indigo' },
	anger: { label: 'Colère', bar: 'bg-clay' },
	sadness: { label: 'Tristesse', bar: 'bg-plum' },
	joy: { label: 'Joie', bar: 'bg-gold' },
	trust: { label: 'Confiance', bar: 'bg-leaf' }
};

/** Codes produced by the analysis: "fr", "nouchi", "en", "und" (undetermined). */
export const LANGUAGES: Record<string, string> = {
	fr: 'Français',
	nouchi: 'Nouchi',
	en: 'Anglais',
	und: 'Indéterminée',
	other: 'Autre'
};

export function languageLabel(code: string): string {
	return LANGUAGES[code] ?? code.toUpperCase();
}

export const FREQUENCIES = [
	{ minutes: 15, label: 'Toutes les 15 minutes' },
	{ minutes: 60, label: 'Toutes les heures' },
	{ minutes: 360, label: 'Toutes les 6 heures' },
	{ minutes: 1440, label: 'Une fois par jour' }
] as const;

export function frequencyLabel(minutes: number): string {
	return (
		FREQUENCIES.find((frequency) => frequency.minutes === minutes)?.label ?? `Toutes les ${minutes} minutes`
	);
}

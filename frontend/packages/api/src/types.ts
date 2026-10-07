// Names for the schemas of the API. schema.d.ts is generated from /openapi.json (pnpm api:types): when the API
// changes, regenerate it and the type checker points at every call to adapt.
import type { components, paths } from './schema.js';

type Schemas = components['schemas'];
type QueryOf<Path extends keyof paths> = paths[Path] extends { get: { parameters: { query?: infer Q } } }
	? NonNullable<Q>
	: never;

export type User = Schemas['UserOut'];
export type Role = Schemas['Role'];
export type UserUpdate = Schemas['UserUpdateIn'];
export type Registration = Schemas['RegisterIn'];
export type TokenPair = Schemas['TokenOut'];

export type Watch = Schemas['WatchOut'];
export type WatchCreate = Schemas['WatchCreate'];
export type WatchUpdate = Schemas['WatchUpdate'];
export type Source = Schemas['SourceKind'];

export type Mention = Schemas['MentionOut'];
export type Sentiment = Schemas['SentimentLabel'];
export type Emotion = Schemas['Emotion'];
export type Stats = Schemas['StatsOut'];
export type Counts = Schemas['CountsOut'];
export type Alert = Schemas['AlertOut'];
export type Places = Schemas['PlacesOut'];
export type Themes = Schemas['ThemesOut'];
export type Theme = Schemas['ThemeOut'];

export interface Page<T> {
	items: T[];
	total: number;
	page: number;
	size: number;
}

export type WatchQuery = QueryOf<'/watches'>;
export type MentionQuery = QueryOf<'/watches/{watch_id}/mentions'>;
export type StatsQuery = QueryOf<'/watches/{watch_id}/stats'>;
export type PlacesQuery = QueryOf<'/watches/{watch_id}/places'>;
export type ThemesQuery = QueryOf<'/watches/{watch_id}/themes'>;
export type AlertQuery = QueryOf<'/watches/{watch_id}/alerts'>;
export type UserQuery = QueryOf<'/users'>;

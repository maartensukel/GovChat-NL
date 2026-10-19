import { describe, expect, it } from 'vitest';

import { resolvePiiMode } from './index';

describe('resolvePiiMode', () => {
	it('staat uit als de beheerder het filter heeft uitgezet', () => {
		expect(resolvePiiMode(false, 'mask', 'mask', 'warn')).toEqual({ mode: 'off', locked: true });
	});

	it('gebruikt de standaard van de beheerder zonder agent- of chatinstelling', () => {
		expect(resolvePiiMode(true, 'warn', null, null)).toEqual({ mode: 'warn', locked: false });
		expect(resolvePiiMode(true, 'off', null, null)).toEqual({ mode: 'off', locked: false });
		expect(resolvePiiMode(true, undefined, null, null)).toEqual({ mode: 'warn', locked: false });
	});

	it('laat de agent de standaard overschrijven', () => {
		expect(resolvePiiMode(true, 'warn', 'off', null)).toEqual({ mode: 'off', locked: false });
		expect(resolvePiiMode(true, 'off', 'warn', null)).toEqual({ mode: 'warn', locked: false });
	});

	it('laat de chat de agent overschrijven', () => {
		expect(resolvePiiMode(true, 'warn', 'warn', 'off')).toEqual({ mode: 'off', locked: false });
		expect(resolvePiiMode(true, 'off', 'off', 'warn')).toEqual({ mode: 'warn', locked: false });
	});

	it('maakt "Altijd filteren" bindend, van agent of beheerder', () => {
		expect(resolvePiiMode(true, 'warn', 'mask', 'off')).toEqual({ mode: 'mask', locked: true });
		expect(resolvePiiMode(true, 'mask', null, 'off')).toEqual({ mode: 'mask', locked: true });
	});

	it('laat een agent een strenge standaard versoepelen', () => {
		expect(resolvePiiMode(true, 'mask', 'warn', null)).toEqual({ mode: 'warn', locked: false });
	});
});

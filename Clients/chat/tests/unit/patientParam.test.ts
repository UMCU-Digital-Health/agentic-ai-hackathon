import { describe, expect, it } from 'vitest'
import { parsePatientId, withPatientId } from '../../src/lib/patientParam'

describe('parsePatientId', () => {
  it('reads a numeric id', () => {
    expect(parsePatientId('?patientId=3')).toBe(3)
  })

  it('is null when absent or not a positive integer', () => {
    expect(parsePatientId('')).toBeNull()
    expect(parsePatientId('?other=1')).toBeNull()
    expect(parsePatientId('?patientId=abc')).toBeNull()
    expect(parsePatientId('?patientId=-1')).toBeNull()
    expect(parsePatientId('?patientId=1.5')).toBeNull()
  })
})

describe('withPatientId', () => {
  it('sets the param and preserves others', () => {
    expect(withPatientId('?theme=dark', 2)).toBe('?theme=dark&patientId=2')
  })

  it('replaces an existing value', () => {
    expect(withPatientId('?patientId=1', 2)).toBe('?patientId=2')
  })

  it('removes the param for null', () => {
    expect(withPatientId('?patientId=1', null)).toBe('')
  })
})

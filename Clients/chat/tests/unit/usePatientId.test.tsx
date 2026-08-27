import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { usePatientId } from '../../src/state/usePatientId'

describe('usePatientId', () => {
  it('reads the id from the URL', () => {
    window.history.replaceState(null, '', '/?patientId=4')
    const { result } = renderHook(() => usePatientId())
    expect(result.current.patientId).toBe(4)
  })

  it('pushes a new URL and re-renders on change', () => {
    const { result } = renderHook(() => usePatientId())
    expect(result.current.patientId).toBeNull()

    act(() => result.current.setPatientId(2))

    expect(window.location.search).toBe('?patientId=2')
    expect(result.current.patientId).toBe(2)
  })

  it('follows the browser Back button', () => {
    const { result } = renderHook(() => usePatientId())
    act(() => result.current.setPatientId(1))
    act(() => result.current.setPatientId(2))

    act(() => {
      window.history.replaceState(null, '', '/?patientId=1')
      window.dispatchEvent(new PopStateEvent('popstate'))
    })

    expect(result.current.patientId).toBe(1)
  })
})

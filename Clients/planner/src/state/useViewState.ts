import { createContext, useContext } from 'react'
import type { Range } from '../lib/ranges'

/** Calendar or list — orthogonal to the range, exactly as the dropdown implies. */
export type ViewMode = 'calendar' | 'list'

export type ViewState = {
  range: Range
  mode: ViewMode
  /** The date the range is resolved around. */
  anchorDate: Date
  setRange: (range: Range) => void
  setMode: (mode: ViewMode) => void
  setAnchorDate: (date: Date) => void
  /** Page one span forward or back. */
  stepBy: (delta: number) => void
  /** Jump back to today without changing the range. */
  goToToday: () => void
}

export const ViewStateContext = createContext<ViewState | null>(null)

export const useViewState = (): ViewState => {
  const value = useContext(ViewStateContext)
  if (!value) throw new Error('useViewState must be used inside a ViewStateProvider')
  return value
}

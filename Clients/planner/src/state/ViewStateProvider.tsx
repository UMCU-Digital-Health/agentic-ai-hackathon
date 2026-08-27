import { useCallback, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Range } from '../lib/ranges'
import { step } from '../lib/ranges'
import type { ViewMode, ViewState } from './useViewState'
import { ViewStateContext } from './useViewState'

type Props = {
  children: ReactNode
  /** Overrides for tests; production always starts on Week + Calendar + today. */
  initialRange?: Range
  initialMode?: ViewMode
  initialDate?: Date
}

export const ViewStateProvider = ({
  children,
  initialRange = 'week',
  initialMode = 'calendar',
  initialDate,
}: Props) => {
  const [range, setRange] = useState<Range>(initialRange)
  const [mode, setMode] = useState<ViewMode>(initialMode)
  const [anchorDate, setAnchorDate] = useState<Date>(() => initialDate ?? new Date())

  const stepBy = useCallback(
    (delta: number) => setAnchorDate((current) => step(range, current, delta)),
    [range],
  )
  const goToToday = useCallback(() => setAnchorDate(new Date()), [])

  const value = useMemo<ViewState>(
    () => ({ range, mode, anchorDate, setRange, setMode, setAnchorDate, stepBy, goToToday }),
    [range, mode, anchorDate, stepBy, goToToday],
  )

  return <ViewStateContext.Provider value={value}>{children}</ViewStateContext.Provider>
}

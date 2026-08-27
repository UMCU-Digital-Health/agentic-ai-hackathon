import { Button, Menu } from '@mantine/core'
import {
  IconCalendarMonth,
  IconCalendarWeek,
  IconChevronDown,
  IconColumns,
  IconColumns1,
  IconColumns3,
  IconList,
} from '@tabler/icons-react'
import type { ReactNode } from 'react'
import type { Range } from '../../lib/ranges'
import { RANGE_LABELS } from '../../lib/ranges'
import { useViewState } from '../../state/useViewState'

const RANGE_ICONS: Record<Range, ReactNode> = {
  day: <IconColumns1 size={16} stroke={1.5} />,
  threeDay: <IconColumns3 size={16} stroke={1.5} />,
  workWeek: <IconColumns size={16} stroke={1.5} />,
  week: <IconCalendarWeek size={16} stroke={1.5} />,
  month: <IconCalendarMonth size={16} stroke={1.5} />,
}

/**
 * `Menu.RadioItem` and `Menu.CheckboxItem` own their left slot for the
 * selection indicator, so the icon sits inline with the label instead. Spans,
 * not a Mantine `Group`, because the item renders as a `<button>`.
 */
const ItemLabel = ({ icon, children }: { icon: ReactNode; children: ReactNode }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
    {icon}
    {children}
  </span>
)

/**
 * Range and view mode are orthogonal, which is why the range is a radio group
 * and `List` is a checkbox below the divider: `Week` and `List` are ticked at
 * the same time.
 */
export const ViewMenu = () => {
  const { range, mode, setRange, setMode } = useViewState()

  return (
    <Menu closeOnItemClick={false} position="bottom-end" width={220}>
      <Menu.Target>
        <Button
          variant="subtle"
          color="dark"
          rightSection={<IconChevronDown size={16} stroke={1.5} />}
        >
          {RANGE_LABELS[range]}
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.RadioGroup value={range} onChange={(value) => setRange(value as Range)}>
          {(Object.keys(RANGE_LABELS) as Range[]).map((candidate) => (
            <Menu.RadioItem key={candidate} value={candidate}>
              <ItemLabel icon={RANGE_ICONS[candidate]}>
                {RANGE_LABELS[candidate]}
              </ItemLabel>
            </Menu.RadioItem>
          ))}
        </Menu.RadioGroup>
        <Menu.Divider />
        <Menu.CheckboxItem
          checked={mode === 'list'}
          onChange={(checked) => setMode(checked ? 'list' : 'calendar')}
        >
          <ItemLabel icon={<IconList size={16} stroke={1.5} />}>List</ItemLabel>
        </Menu.CheckboxItem>
      </Menu.Dropdown>
    </Menu>
  )
}

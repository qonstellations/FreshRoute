// Presenter story bar (ARCHITECTURE §16, D-24): floating pill with beat title, progress dots, prev/next.
import { ActionIcon, Group, Paper, Text, Tooltip } from '@mantine/core'
import { IconChevronLeft, IconChevronRight, IconX } from '@tabler/icons-react'
import { AnimatePresence, m } from 'motion/react'
import { BEATS } from '../lib/story'
import { spring } from '../theme'

type Props = { open: boolean; beat: number; onJump: (i: number) => void; onExit: () => void }

export function StoryBar({ open, beat, onJump, onExit }: Props) {
  const b = BEATS[beat]
  return (
    <AnimatePresence>
      {open && (
        <m.div key="storybar" className="story-bar" initial={{ opacity: 0, y: 80, x: '-50%' }}
          animate={{ opacity: 1, y: 0, x: '-50%' }} exit={{ opacity: 0, y: 80, x: '-50%' }} transition={spring.bouncy}>
          <Paper shadow="xl" radius="xl" px="md" py={8} withBorder className="story-pill">
            <Group gap="sm" wrap="nowrap">
              <ActionIcon variant="subtle" radius="xl" size="lg" aria-label="Previous beat"
                disabled={beat === 0} onClick={() => onJump(beat - 1)}><IconChevronLeft /></ActionIcon>
              <div style={{ minWidth: 260 }}>
                <Text size="xs" c="dimmed" fw={600} tt="uppercase">{b.tab} · {beat + 1} / {BEATS.length}</Text>
                <AnimatePresence mode="wait" initial={false}>
                  <m.div key={beat} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }} transition={spring.snappy}>
                    <Text fw={700} size="lg" lh={1.2}>{b.title}</Text>
                  </m.div>
                </AnimatePresence>
                <Group gap={6} mt={6} wrap="nowrap">
                  {BEATS.map((x, i) => (
                    <button key={i} type="button" className="story-dot" aria-label={`Beat ${i + 1}: ${x.title}`}
                      aria-current={i === beat ? 'step' : undefined} onClick={() => onJump(i)}>
                      {i === beat && <m.span layoutId="story-dot" className="story-dot-on" transition={spring.snappy} />}
                    </button>
                  ))}
                </Group>
              </div>
              <ActionIcon variant="filled" radius="xl" size="lg" aria-label="Next beat"
                disabled={beat === BEATS.length - 1} onClick={() => onJump(beat + 1)}><IconChevronRight /></ActionIcon>
              <Tooltip label="Exit (Esc)">
                <ActionIcon variant="subtle" color="gray" radius="xl" aria-label="Exit story mode" onClick={onExit}>
                  <IconX size={16} />
                </ActionIcon>
              </Tooltip>
            </Group>
          </Paper>
        </m.div>
      )}
    </AnimatePresence>
  )
}

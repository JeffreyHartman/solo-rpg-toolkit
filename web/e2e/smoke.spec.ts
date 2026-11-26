import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { expect, test } from './fixtures.ts'

// Fixed dice, in the order the engine asks for them.
const DICE = [
  ...Array(18).fill(4), 6, // Tess: 3d6 x6 (all 12s), d8 hit points
  1, 1, //                    explore 1: map table (hall), encounter table (no encounter)
  8, //                       confirmed STR check: 8 against 12, a success
  6, 15, 1, 4, 3, 5, 2, //    explore 2: map (chamber), encounter (combat), foes (two goblins), their HP, initiative
  6, //                       wandering monster check (d6): no encounter
  15, 6, 1, 1, 5, 5, 2, //    attack 1 hits and kills a goblin, the other goblin misses, round 2 initiative
  18, 6, //                   attack 2 kills the last goblin
]

const NOTE = 'Sessions/Session 001 - First Delve.md'

// One list of steps per Referee turn. Every engine event of a click or an answer starts a turn.
const REFEREE = [
  [{ say: 'Tess checks her gear.' }],
  [{ say: 'A hall opens ahead.' }],
  [
    { say: 'You set your shoulder to the door.' },
    {
      call: {
        tool: 'mcp__engine__propose',
        input: { procedure: 'ability_check', inputs: { member: 'Tess', ability: 'STR' }, reason: 'Tess shoulders the stuck door.' },
      },
    },
  ],
  [{ say: 'The door gives way.' }],
  [
    {
      call: {
        tool: 'mcp__engine__judgment_call',
        input: {
          category: 'rules', question: 'Can Tess climb the rope in chain mail?',
          options: ['yes', 'no'], suggestion: 'yes', reason: 'The rules do not say.',
        },
      },
    },
  ],
  [{ say: 'Tess climbs the rope.' }],
  [{ say: 'Two goblins leap out.' }],
  [{ say: 'Tess cuts one goblin down.' }],
  [{ say: 'The last goblin falls.' }],
  [
    {
      call: {
        tool: 'Write',
        input: { file_path: NOTE, content: '---\ntype: session\nsession: 1\n---\n# First Delve\n\nTess beat two goblins.\n' },
      },
    },
    { say: 'Wrote the note.' },
  ],
]

test('a short delve from a new campaign to the session note', async ({ page, launchScripted }) => {
  const harness = await launchScripted({ dice: DICE, referee: REFEREE })
  await page.goto(harness.url)

  // New campaign and character.
  await page.getByLabel('Name').fill('Smoke Test')
  await page.getByLabel('flextale').check()
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByText('Create your character').waitFor()
  await page.getByLabel('Name').fill('Tess')
  await page.getByRole('button', { name: 'Roll character' }).click()
  await expect(page.getByText('Tess the Fighter joins the party.')).toBeVisible()
  await expect(page.getByText('Tess checks her gear.')).toBeVisible()

  // Explore two areas: an exit marker on the map, then an action button.
  await page.locator('g.exit').nth(1).click()
  await expect(page.locator('svg text', { hasText: 'Area 2' })).toBeVisible()
  await expect(page.getByText('A hall opens ahead.')).toBeVisible()

  // A proposal from free text: the card, then its mechanics card.
  await page.getByLabel('Free text for the Referee').fill('I shove the door.')
  await page.getByRole('button', { name: 'Send' }).click()
  const proposal = page.locator('article.proposal')
  await expect(proposal).toContainText('Ability check')
  await expect(proposal).toContainText("Tess's STR score")
  await proposal.getByRole('button', { name: 'Confirm' }).click()
  const check = page.locator('.card').filter({ hasText: '[8] = 8 vs 12' })
  await expect(check).toContainText('Success')
  await expect(check).toContainText("Tess's STR score")
  await expect(page.getByText('The door gives way.')).toBeVisible()
  await expect(proposal).toHaveCount(0)

  // A judgment call from free text.
  await page.getByLabel('Free text for the Referee').fill('I climb the rope.')
  await page.getByRole('button', { name: 'Send' }).click()
  const judgment = page.locator('article.judgment')
  await expect(judgment).toContainText('Can Tess climb the rope in chain mail?')
  await judgment.getByRole('button', { name: 'yes' }).click()
  await expect(page.getByText('Tess climbs the rope.')).toBeVisible()
  await expect(judgment).toHaveCount(0)

  // The second area starts a fight: the combat panel lists both goblins.
  await page.getByRole('button', { name: /^Explore the/ }).first().click()
  await expect(page.locator('svg text', { hasText: 'Area 3' })).toBeVisible()
  const combat = page.locator('.panel.combat')
  await expect(combat).toContainText('goblin m1')
  await expect(combat).toContainText('HP 4/4')
  await expect(combat).toContainText('goblin m2')
  await expect(combat).toContainText('HP 3/3')
  for (const size of [{ width: 1280, height: 800 }, { width: 1024, height: 700 }]) {
    await page.setViewportSize(size)
    for (const part of [combat.locator('b'), combat.locator('li').first()]) {
      const covered = await part.evaluate((el) => {
        const r = el.getBoundingClientRect()
        return !el.contains(el.ownerDocument.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2))
      })
      expect(covered, `combat panel part covered at ${size.width}x${size.height}`).toBe(false)
    }
  }
  await page.setViewportSize({ width: 1280, height: 800 })

  await page.getByRole('button', { name: /^Tess attacks goblin m1/ }).click()
  await expect(combat).toContainText('dead')
  await expect(page.getByText('The Referee is working…')).toHaveCount(0)
  await page.getByRole('button', { name: /^Tess attacks goblin m2/ }).click()
  await expect(page.getByText('Combat ends: victory.')).toBeVisible()
  await expect(combat).toHaveCount(0)

  // End the session: the Referee writes the note and the next session starts.
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'End session' }).click()
  await expect(page.getByText(`Session note written: ${NOTE}. Session 2 begins.`)).toBeVisible()
  const vault = join(harness.campaigns, readdirSync(harness.campaigns)[0], 'vault')
  expect(readFileSync(join(vault, NOTE), 'utf8')).toContain('Tess beat two goblins.')
  expect(existsSync(join(vault, 'Sessions', 'Raw', 'Session 001.md'))).toBe(true)
})

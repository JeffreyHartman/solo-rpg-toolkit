import { mkdirSync } from 'node:fs'
import { sendMessage, test } from './fixtures.ts'

const shots = 'e2e-output/screenshots'
mkdirSync(shots, { recursive: true })

const BRANNOC = {
  name: 'Brannoc', class: 'Fighter', level: 1, hp: 6, max_hp: 6, ac: 5,
  abilities: { STR: 14, DEX: 12, CON: 11, INT: 9, WIS: 10, CHA: 8 },
  saves: { death: 12, wands: 13, paralysis: 14, breath: 15, spells: 16 },
}

const withBrannoc = (state: Record<string, any>) => {
  state.party.members = [BRANNOC]
}

test('map', async ({ page, launch }) => {
  const harness = await launch({ editState: withBrannoc })
  await page.goto(harness.url)
  await page.getByText('Gatehouse').first().waitFor()
  await page.screenshot({ path: `${shots}/map.png` })
})

test('proposal card', async ({ page, launch }) => {
  const harness = await launch({ editState: withBrannoc })
  await page.goto(harness.url)
  await page.getByText('Gatehouse').first().waitFor()
  await sendMessage(harness, {
    type: 'act',
    command: {
      type: 'propose', procedure: 'ability_check', inputs: { member: 'Brannoc', ability: 'STR' },
      reason: 'Brannoc shoulders the stuck gate.',
    },
  })
  await page.getByText('Ability check').first().waitFor()
  await page.screenshot({ path: `${shots}/proposal.png` })
})

test('judgment call', async ({ page, launch }) => {
  const harness = await launch({ editState: withBrannoc })
  await page.goto(harness.url)
  await page.getByText('Gatehouse').first().waitFor()
  await sendMessage(harness, {
    type: 'act',
    command: {
      type: 'judgment', category: 'rules', question: 'Can Brannoc climb the rope in plate?',
      options: ['yes', 'no'], suggestion: 'yes', reason: 'The rules do not say.',
    },
  })
  await page.getByText('Can Brannoc climb the rope in plate?').first().waitFor()
  await page.screenshot({ path: `${shots}/judgment.png` })
})

test('combat', async ({ page, launch }) => {
  const harness = await launch({
    editState: (state) => {
      withBrannoc(state)
      const goblin = (id: string, hp: number) => ({
        id, name: 'goblin', hp, max_hp: 4, ac: 6, thac0: 19, damage: '1d6', status: 'alive', generic: false,
      })
      state.combat = {
        area: state.party.area, outcome: null, round: 1, phase: 'party', first: 'party', acted: [],
        monsters: [goblin('m1', 4), goblin('m2', 3)],
      }
    },
  })
  await page.goto(harness.url)
  await page.getByText('goblin').first().waitFor()
  await page.screenshot({ path: `${shots}/combat.png` })
})

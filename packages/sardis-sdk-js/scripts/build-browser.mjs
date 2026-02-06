import { rollup } from 'rollup'
import config from '../rollup.config.js'

async function main() {
  const { output, ...inputOptions } = config
  const outputs = Array.isArray(output) ? output : [output]

  const bundle = await rollup(inputOptions)
  try {
    for (const outputOptions of outputs) {
      await bundle.write(outputOptions)
    }
  } finally {
    await bundle.close()
  }

  const written = outputs
    .map((entry) => ('file' in entry ? entry.file : null))
    .filter(Boolean)
    .join(', ')

  console.log(`Browser bundle created: ${written}`)
}

main()
  .then(() => {
    process.exit(0)
  })
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })

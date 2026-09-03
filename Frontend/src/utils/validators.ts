// Composable field validators. Each returns a validate() function that
// takes a value and returns an error string, or null if valid.
// Usage: runValidators(value, [required(), minLength(8)])

export type Validator = (value: string) => string | null

export function required(message = 'This field is required.'): Validator {
  return (value) => (value.trim().length > 0 ? null : message)
}

export function minLength(min: number, message?: string): Validator {
  return (value) =>
    value.length >= min ? null : (message ?? `Must be at least ${min} characters.`)
}

export function email(message = 'Enter a valid email address.'): Validator {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return (value) => (value.trim() === '' || pattern.test(value) ? null : message)
}

export function matches(getOtherValue: () => string, message = 'Passwords do not match.'): Validator {
  return (value) => (value === getOtherValue() ? null : message)
}

export function pattern(regex: RegExp, message: string): Validator {
  return (value) => (regex.test(value) ? null : message)
}

export function numberRange(min: number, max: number, message?: string): Validator {
  return (value) => {
    const n = Number(value)
    if (Number.isNaN(n)) return message ?? 'Must be a number.'
    return n >= min && n <= max ? null : (message ?? `Must be between ${min} and ${max}.`)
  }
}

/** Runs validators in order, returning the first error encountered (or null). */
export function runValidators(value: string, validators: Validator[]): string | null {
  for (const validate of validators) {
    const error = validate(value)
    if (error) return error
  }
  return null
}
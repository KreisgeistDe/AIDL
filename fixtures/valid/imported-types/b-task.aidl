module fixtures.valid.task

import fixtures.valid.shared.Priority

export value Task {
  title: string required
  priority: Priority required
}

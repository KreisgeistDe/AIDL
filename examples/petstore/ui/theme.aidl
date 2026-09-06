module petstore.ui.theme

export theme PetTheme {
  color primary "#2563EB"
  color surface "#FFFFFF"
  color text "#17202A"
  color danger "#B42318"
  color success "#15803D"
  color muted "#667085"
  spacing scale [4, 8, 12, 16, 24, 32]
  radius card 12
  typography body system(16, 1.5)
  typography heading system(28, 1.2, weight: 700)
  contrast minimum AA
}


import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/chat/chat-shell.component').then((m) => m.ChatShellComponent),
  },
  { path: '**', redirectTo: '' },
];

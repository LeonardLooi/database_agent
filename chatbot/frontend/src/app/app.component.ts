import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  styles: [':host { display: block; height: 100%; }'],
  template: `<router-outlet />`,
})
export class AppComponent {}

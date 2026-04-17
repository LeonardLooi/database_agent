# AI Chat Quick Start

Minimal wiring for Angular 21 and Flutter 3.41.x. Load this when starting a new chat feature from scratch.

---

## Angular 21

```typescript
// features/chat/chat.component.ts — entry point
@Component({
  selector: 'app-chat',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StreamingMessageComponent, ChatInputComponent, TokenIndicatorComponent],
  template: `
    <div class="flex flex-col h-full">
      <app-token-indicator [usage]="tokenUsage()" />
      <div #scrollContainer class="flex-1 overflow-y-auto p-4 space-y-2"
           role="log" aria-live="polite" aria-label="Conversation">
        @for (msg of messages(); track msg.id) {
          <app-streaming-message [message]="msg" />
        }
      </div>
      <app-chat-input (send)="onSend($event)" (stop)="onStop()" [streaming]="isStreaming()" />
    </div>
  `
})
export class ChatComponent { ... }
```

Full implementation with `AbortController`, `AutoScrollService`, and `ErrorHandler` → `reference/streaming-patterns.md`

---

## Flutter 3.41.x

```dart
// features/chat/presentation/screens/chat_screen.dart — entry point
class ChatScreen extends ConsumerWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(chatNotifierProvider);
    return Column(children: [
      TokenIndicatorWidget(usage: state.tokenUsage),
      Expanded(child: ChatMessageList(messages: state.messages)),
      ChatInputWidget(
        onSend: (text) => ref.read(chatNotifierProvider.notifier).send(text),
        isStreaming: state.isStreaming,
      ),
    ]);
  }
}
```

Full implementation with `AsyncNotifier`, `ScrollController`, and reduced-motion check → `reference/streaming-patterns.md`

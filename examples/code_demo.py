"""Code Demo - Demonstrates syntax-highlighted code with CodeBlock.

This example shows the CodeBlock element with:
- Syntax highlighting for multiple languages
- Line numbers
- Scrolling for long files
- Border styles and titles
- Language switching
- Theme support

Run with: python examples/code_demo.py

Controls:
- Arrow keys: Scroll up/down
- Page Up/Down: Scroll by page
- Home/End: Jump to top/bottom
- Mouse wheel: Scroll content
- 1-4: Switch between code examples
- q: Quit
"""

import shutil

from wijjit import (
    Wijjit,
)
from wijjit.core.events import EventType, HandlerScope
from wijjit.elements.display.code import CodeBlock

# Sample code in different languages
PYTHON_CODE = '''def fibonacci(n):
    """Generate Fibonacci sequence up to n terms.

    Parameters
    ----------
    n : int
        Number of terms to generate

    Returns
    -------
    list
        Fibonacci sequence
    """
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[-1] + fib[-2])

    return fib


class FibonacciGenerator:
    """A class-based approach to generating Fibonacci numbers."""

    def __init__(self, max_terms=10):
        self.max_terms = max_terms
        self._cache = {}

    def get_term(self, n):
        """Get the nth Fibonacci number (memoized)."""
        if n in self._cache:
            return self._cache[n]

        if n <= 1:
            result = n
        else:
            result = self.get_term(n - 1) + self.get_term(n - 2)

        self._cache[n] = result
        return result

    def generate_sequence(self):
        """Generate the full sequence up to max_terms."""
        return [self.get_term(i) for i in range(self.max_terms)]


# Usage example
if __name__ == "__main__":
    # Simple function approach
    print("Using function:")
    fib_list = fibonacci(10)
    print(f"First 10 Fibonacci numbers: {fib_list}")

    # Class-based approach
    print("\\nUsing class:")
    gen = FibonacciGenerator(max_terms=10)
    sequence = gen.generate_sequence()
    print(f"Sequence: {sequence}")
'''

JAVASCRIPT_CODE = '''// Async/await example with error handling
async function fetchUserData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching user data:', error);
        throw error;
    }
}

// React component example
function UserProfile({ userId }) {
    const [user, setUser] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
        let cancelled = false;

        async function loadUser() {
            try {
                setLoading(true);
                const userData = await fetchUserData(userId);

                if (!cancelled) {
                    setUser(userData);
                    setError(null);
                }
            } catch (err) {
                if (!cancelled) {
                    setError(err.message);
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }

        loadUser();

        return () => {
            cancelled = true;
        };
    }, [userId]);

    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;
    if (!user) return <div>No user found</div>;

    return (
        <div className="user-profile">
            <h2>{user.name}</h2>
            <p>Email: {user.email}</p>
            <p>Joined: {new Date(user.createdAt).toLocaleDateString()}</p>
        </div>
    );
}

export default UserProfile;
'''

RUST_CODE = '''use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::task;

/// A thread-safe cache with automatic expiry
pub struct ExpiringCache<K, V> {
    data: Arc<Mutex<HashMap<K, CacheEntry<V>>>>,
    ttl_seconds: u64,
}

struct CacheEntry<V> {
    value: V,
    expires_at: std::time::Instant,
}

impl<K: Eq + std::hash::Hash + Clone, V: Clone> ExpiringCache<K, V> {
    /// Create a new cache with the specified TTL
    pub fn new(ttl_seconds: u64) -> Self {
        Self {
            data: Arc::new(Mutex::new(HashMap::new())),
            ttl_seconds,
        }
    }

    /// Insert a value into the cache
    pub fn insert(&self, key: K, value: V) {
        let mut data = self.data.lock().unwrap();
        data.insert(key, CacheEntry {
            value,
            expires_at: std::time::Instant::now()
                + std::time::Duration::from_secs(self.ttl_seconds),
        });
    }

    /// Get a value from the cache if it exists and hasn't expired
    pub fn get(&self, key: &K) -> Option<V> {
        let mut data = self.data.lock().unwrap();

        if let Some(entry) = data.get(key) {
            if std::time::Instant::now() < entry.expires_at {
                return Some(entry.value.clone());
            } else {
                // Entry has expired, remove it
                data.remove(key);
            }
        }

        None
    }

    /// Clean up expired entries
    pub fn cleanup(&self) {
        let mut data = self.data.lock().unwrap();
        let now = std::time::Instant::now();
        data.retain(|_, entry| now < entry.expires_at);
    }

    /// Get the number of entries in the cache
    pub fn len(&self) -> usize {
        self.data.lock().unwrap().len()
    }

    /// Check if the cache is empty
    pub fn is_empty(&self) -> bool {
        self.data.lock().unwrap().is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cache_expiry() {
        let cache = ExpiringCache::<String, i32>::new(1);
        cache.insert("key".to_string(), 42);

        assert_eq!(cache.get(&"key".to_string()), Some(42));

        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

        assert_eq!(cache.get(&"key".to_string()), None);
    }
}
'''

GO_CODE = '''package main

import (
    "context"
    "fmt"
    "sync"
    "time"
)

// Worker represents a concurrent worker that processes jobs
type Worker struct {
    id       int
    jobChan  <-chan Job
    resultChan chan<- Result
    wg       *sync.WaitGroup
}

// Job represents a unit of work
type Job struct {
    ID      int
    Data    string
    Timeout time.Duration
}

// Result represents the result of processing a job
type Result struct {
    JobID   int
    Success bool
    Data    string
    Error   error
}

// NewWorker creates a new worker
func NewWorker(id int, jobChan <-chan Job, resultChan chan<- Result, wg *sync.WaitGroup) *Worker {
    return &Worker{
        id:       id,
        jobChan:  jobChan,
        resultChan: resultChan,
        wg:       wg,
    }
}

// Start begins processing jobs
func (w *Worker) Start(ctx context.Context) {
    defer w.wg.Done()

    for {
        select {
        case <-ctx.Done():
            fmt.Printf("Worker %d shutting down\\n", w.id)
            return
        case job, ok := <-w.jobChan:
            if !ok {
                fmt.Printf("Worker %d: job channel closed\\n", w.id)
                return
            }
            w.processJob(ctx, job)
        }
    }
}

// processJob processes a single job with timeout
func (w *Worker) processJob(ctx context.Context, job Job) {
    ctx, cancel := context.WithTimeout(ctx, job.Timeout)
    defer cancel()

    resultChan := make(chan Result, 1)

    go func() {
        // Simulate work
        time.Sleep(100 * time.Millisecond)
        resultChan <- Result{
            JobID:   job.ID,
            Success: true,
            Data:    fmt.Sprintf("Processed by worker %d: %s", w.id, job.Data),
        }
    }()

    select {
    case result := <-resultChan:
        w.resultChan <- result
    case <-ctx.Done():
        w.resultChan <- Result{
            JobID:   job.ID,
            Success: false,
            Error:   fmt.Errorf("job %d timed out", job.ID),
        }
    }
}

func main() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    numWorkers := 5
    jobChan := make(chan Job, 100)
    resultChan := make(chan Result, 100)
    var wg sync.WaitGroup

    // Start workers
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        worker := NewWorker(i, jobChan, resultChan, &wg)
        go worker.Start(ctx)
    }

    // Send jobs
    for i := 0; i < 20; i++ {
        jobChan <- Job{
            ID:      i,
            Data:    fmt.Sprintf("Job data %d", i),
            Timeout: 1 * time.Second,
        }
    }
    close(jobChan)

    // Wait for all workers to finish
    wg.Wait()
    close(resultChan)

    // Process results
    for result := range resultChan {
        if result.Success {
            fmt.Printf("Job %d: %s\\n", result.JobID, result.Data)
        } else {
            fmt.Printf("Job %d failed: %v\\n", result.JobID, result.Error)
        }
    }
}
'''


def create_app():
    """Create and configure the code demo application.

    Returns
    -------
    Wijjit
        Configured application instance
    """
    # Get terminal size
    term_size = shutil.get_terminal_size()
    code_width = min(90, term_size.columns - 4)
    code_height = min(35, term_size.lines - 8)

    # Initialize app with state
    app = Wijjit(initial_state={
        "current_example": 0,
        "examples": [
            {"name": "Python", "code": PYTHON_CODE, "lang": "python"},
            {"name": "JavaScript", "code": JAVASCRIPT_CODE, "lang": "javascript"},
            {"name": "Rust", "code": RUST_CODE, "lang": "rust"},
            {"name": "Go", "code": GO_CODE, "lang": "go"},
        ],
    })

    # Create CodeBlock element
    example = app.state["examples"][0]
    codeblock = CodeBlock(
        id="code",
        code=example["code"],
        language=example["lang"],
        width=code_width,
        height=code_height,
        border_style="double",
        title=f"Example: {example['name']}",
        show_line_numbers=True,
        theme="monokai",
    )

    # Register with focus manager
    app.focus_manager.set_elements([codeblock])
    codeblock.on_focus()

    @app.view("main", default=True)
    def main_view():
        """Main view with code display."""
        def render_data():
            # Update codeblock if example changed
            current_idx = app.state["current_example"]
            example = app.state["examples"][current_idx]
            codeblock.set_code(example["code"], example["lang"])
            codeblock.title = f"Example: {example['name']}"

            # Build menu
            menu_items = []
            for i, ex in enumerate(app.state["examples"]):
                if i == current_idx:
                    menu_items.append(f"[{i+1}] {ex['name']} <--")
                else:
                    menu_items.append(f"[{i+1}] {ex['name']}")
            menu_text = "  ".join(menu_items)

            content_text = "\n".join([
                "=" * term_size.columns,
                "  CODE DEMO - Syntax Highlighting".center(term_size.columns),
                "=" * term_size.columns,
                "",
                codeblock.render(),
                "",
                "=" * term_size.columns,
                f"  {menu_text}",
                "  [Arrows/PgUp/PgDn] Scroll  [Home/End] Jump  [1-4] Switch Example  [q] Quit",
                "=" * term_size.columns,
            ])

            return {"content": content_text}

        data = render_data()

        return {
            "template": "{{ content }}",
            "data": data,
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers."""
        def on_key(event):
            """Handle keyboard events."""
            # Quit with 'q'
            if event.key == "q":
                app.quit()
                event.cancel()
                return

            # Switch examples with 1-4 keys
            if event.key in ["1", "2", "3", "4"]:
                idx = int(event.key) - 1
                if 0 <= idx < len(app.state["examples"]):
                    app.state["current_example"] = idx
                    app.refresh()
                event.cancel()
                return

        # Register key handler
        app.on(EventType.KEY, on_key, scope=HandlerScope.VIEW, view_name="main", priority=100)

    return app


def main():
    """Run the code demo application."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

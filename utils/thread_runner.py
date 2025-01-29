import threading
import time


class ThreadRunner:
    """
    A class to run a function in a separate thread with timeout control.
    """

    def __init__(self, func, timeout=None):
        """
        Initializes the ThreadRunner.

        Args:
            func: The function to be executed in a thread.
            timeout: The timeout in seconds. If None, no timeout is set.
        """
        self.func = func
        self.timeout = timeout
        self.thread = None
        self.result = None
        self.exception = None
        self.finished_event = threading.Event()  # Event to signal completion or timeout

    def run(self, *args, **kwargs):
        """
        Runs the function in a new thread.

        Args:
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """

        def target_func():
            """
            Wrapper function to execute the target function and handle results/exceptions.
            """
            try:
                self.result = self.func(*args, **kwargs)
            except Exception as e:
                self.exception = e
            finally:
                self.finished_event.set()  # Signal that the function has finished (or an exception occurred)

        self.thread = threading.Thread(target=target_func)
        self.thread.daemon = True  # Allow the main thread to exit even if this thread is running
        self.thread.start()

        if self.timeout:
            self.finished_event.wait(self.timeout)  # Wait for either completion or timeout

            if not self.finished_event.is_set():
                # Timeout occurred
                print("Thread timed out!")
                # Note: Threads cannot be forcibly terminated in Python.
                #       The thread might still be running in the background.
                #       Best practice is to design your function to be able to handle
                #       termination signals gracefully if you need precise timeout control.

    def get_result(self):
        """
        Returns the result of the function if it completed successfully.

        Returns:
            The result of the function or None if it hasn't finished or timed out.

        Raises:
            Exception: If the function raised an exception, it's re-raised here.
        """
        if self.finished_event.is_set():  # Only return result if the thread has finished
            if self.exception:
                raise self.exception
            return self.result
        else:
            return None  # Still running or timed out

    def is_running(self):
        """
        Check if the thread is still running.

        Returns:
            True if the thread is alive, False otherwise.
        """
        return self.thread is not None and self.thread.is_alive()
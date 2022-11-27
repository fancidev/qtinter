import asyncio


__all__ = "run_task",


def run_task(coro, *, allow_task_nesting=True, **kwargs):
    """Create a Task and eagerly executes the first step."""

    # If allow_task_nesting is True, this function may be called from
    # a running task.  The calling task is 'suspended' before executing
    # the first step of the created task and 'resumed' after the first
    # step completes.

    loop = asyncio.get_running_loop()

    current_task = asyncio.tasks.current_task(loop)
    if current_task is not None and not allow_task_nesting:
        raise RuntimeError("cannot call run_task from a running task "
                           "when allow_task_nesting is False")

    # asyncio.create_task() schedules asyncio.Task.__step to the end of the
    # loop's _ready queue.
    ntodo = len(loop._ready)

    task = asyncio.create_task(coro, **kwargs)
    # if task._source_traceback:
    #     del task._source_traceback[-1]

    assert len(loop._ready) == ntodo + 1
    handle = loop._ready.pop()

    if current_task is not None:
        asyncio.tasks._leave_task(loop, current_task)
    try:
        # The following call only propagates SystemExit and KeyboardInterrupt.
        handle._run()
    finally:
        if current_task is not None:
            asyncio.tasks._enter_task(loop, current_task)

    # Return the task object that encapsulates the remainder of the coroutine.
    return task

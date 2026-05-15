from tgm.core.types import Feedback, FeedbackSample, Message


def group_feedback_by_chat(feedback_items: list[Feedback]) -> dict[int, list[Feedback]]:
    grouped: dict[int, list[Feedback]] = {}
    for feedback in feedback_items:
        grouped.setdefault(feedback.chat_id, []).append(feedback)
    return grouped


def build_feedback_samples(
    feedback_items: list[Feedback],
    messages_by_pair: dict[tuple[int, int], Message],
) -> list[FeedbackSample]:
    samples: list[FeedbackSample] = []
    for feedback in feedback_items:
        ordered_messages: list[Message] = []
        for message_id in feedback.message_ids:
            message = messages_by_pair.get((feedback.chat_id, message_id))
            if message is not None:
                ordered_messages.append(message)
        samples.append(FeedbackSample(user_comment=feedback.user_comment, messages=ordered_messages))
    return samples

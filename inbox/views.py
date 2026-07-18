from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from assistant.models import AppointmentRequest, Conversation, Message
from channels.senders import send_reply

from .models import clinics_for


@login_required
def conversation_list(request):
    clinics = clinics_for(request.user)
    conversations = (
        Conversation.objects.filter(clinic__in=clinics)
        .select_related("clinic")
        .order_by("-updated_at")
    )
    return render(
        request,
        "inbox/conversation_list.html",
        {"conversations": conversations},
    )


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(
        Conversation, pk=pk, clinic__in=clinics_for(request.user)
    )
    return render(
        request,
        "inbox/conversation_detail.html",
        {
            "conversation": conversation,
            "messages_list": conversation.messages.all(),
        },
    )


@login_required
@require_POST
def send_operator_reply(request, pk):
    conversation = get_object_or_404(
        Conversation, pk=pk, clinic__in=clinics_for(request.user)
    )
    text = (request.POST.get("text") or "").strip()
    if text:
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.OPERATOR,
            text=text,
        )
        # Operator ələ aldı → bot susdurulur
        if not conversation.bot_paused:
            conversation.bot_paused = True
            conversation.save(update_fields=["bot_paused", "updated_at"])
        send_reply(conversation, text)
    return redirect("inbox:conversation_detail", pk=pk)


@login_required
@require_POST
def toggle_bot(request, pk):
    conversation = get_object_or_404(
        Conversation, pk=pk, clinic__in=clinics_for(request.user)
    )
    conversation.bot_paused = not conversation.bot_paused
    conversation.save(update_fields=["bot_paused", "updated_at"])
    return redirect("inbox:conversation_detail", pk=pk)


@login_required
def appointment_list(request):
    clinics = clinics_for(request.user)
    appointments = (
        AppointmentRequest.objects.filter(clinic__in=clinics)
        .select_related("clinic")
        .order_by("-created_at")
    )
    return render(
        request,
        "inbox/appointment_list.html",
        {"appointments": appointments},
    )

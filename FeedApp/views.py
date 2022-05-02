from cmath import log
from multiprocessing import context
from django.dispatch import receiver
from django.shortcuts import render, redirect
from .forms import PostForm,ProfileForm, RelationshipForm
from .models import Post, Comment, Like, Profile, Relationship
from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.http import Http404


# Create your views here.

# When a URL request matches the pattern we just defined, 
# Django looks for a function called index() in the views.py file. 

def index(request):
    """The home page for Learning Log."""
    return render(request, 'FeedApp/index.html')



@login_required
def profile(request):
    #checking to see if they have a profile first, if not we create one for them
    profile = Profile.objects.filter(user=request.user) #request.user refers to the one who is logged on and using the system
    if not profile.exists():
        #checking to see if the first line brought back any data
        #if not then we will create it for them
        Profile.objects.create(user=request.user)#this creates a file for them
    profile = Profile.objects.get(user=request.user)

    if request.method != 'POST':
        form = ProfileForm(instance=profile)
    else:
        form = ProfileForm(instance=profile,data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('FeedApp:profile')#this keeps the user on the profile page 
    
    context = {'form': form}
    return render(request, 'FeedApp/profile.html', context)

@login_required
def myfeed(request):
    comment_count_list = []
    like_count_list = []
    posts = Post.objects.filter(username=request.user).order_by('-date_posted')#ordering them by the newest post showing at the top by using orderby
    for p in posts:
        c_count = Comment.objects.filter(post=p).count()
        l_count = Like.objects.filter(post=p).count()
        #these above count likes and comments
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts,comment_count_list,like_count_list)

    context = {'posts':posts, 'zipped_list':zipped_list}
    return render(request, 'FeedApp/myfeed.html', context)


@login_required
def new_post(request):
    if request.method != 'POST':
        form = PostForm()
    else:
        form = PostForm(request.POST,request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False) #commit but not actually writing it to the database
            new_post.username = request.user
            new_post.save()
            return redirect('FeedApp:myfeed')
    
    context = {'form':form}
    return render(request, 'FeedApp/new_post.html', context)

@login_required
def friendsfeed(request):
    comment_count_list = []
    like_count_list = []
    friends = Profile.objects.filter(user=request.user).values('friends')
    posts = Post.objects.filter(username_in=friends).order_by('-date_posted')
    for p in posts:
        c_count = Comment.objects.filter(post=p).count()
        l_count = Like.objects.filter(post=p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts,comment_count_list,like_count_list)

    if request.method == 'POST' and request.POST.get("like"):
        post_to_like = request.POST.get("like")#this is the name of the button 'like'
        print(post_to_like)
        like_already_exists = Like.objects.filter(post_id=post_to_like,username=request.user)#this is to prevent user from liking the post multiple times 
        if not like_already_exists():
            Like.objects.create(post_id=post_to_like,username=request.user)
            return redirect("FeedApp:friendsfeed")#this will refresh the page 

    context = {'posts':posts, 'zipped_list':zipped_list}
    return render(request, 'FeedApp/friendsfeed.html', context)


@login_required
def comments(request, post_id):#want to see if someone has clicked on the comments
    #we want the comments to be a link that will take the user to the comments section wehre they will be able to leave a comment
    #checking to see if a button has been pressed
    if request.method == 'POST' and request.POST.get("btn1"):#checking to see if the request method is post and whether it was clicked
        comment = request.POST.get("comment")#box is named comment
        #getting whatever text is in the box
        Comment.objects.create(post_id=post_id,username=request.user,text=comment,date_added=date.today()) #we have post_id in the parantheses above, assign the id to the id 
        #check at models.py 

    #refresh and comment will show upu on the same page, this is what we are doing next 
    #if request processed if someone hits the submit button 

    comments = Comment.objects.filter(post=post_id)
    post = Post.objects.get(id=post_id)

    context = {'post':post, 'comments':comments}

    return render(request, 'FeedApp/comments.html',context)


@login_required
def friends(request):
    #get the admin_profile and user profile to create the first relationship
    admin_profile = Profile.objects.get(user=1)
    user_profile = Profile.objects.get(user=request.user)

    #to get the friends
    user_friends = user_profile.friends.all()
    user_friends_profiles = Profile.objects.filter(user_in=user_friends)

    #to get friend requests sent
    user_relationships = Relationship.objects.filter(sender=user_profile)
    request_sent_profiles = user_relationships.values('receiver')

    #a list of who we can send a friend request to, show everyone in the system that has requested or we have requested
    all_profiles = Profile.objects.exclude(user=request.user).exclude(id_in=user_friends_profiles).exclude(id_in=request_sent_profiles)
    #exlude the user, the friends we have, and the request we have sent

    #friend requests received by the user
    request_received_profiles = Relationship.objects.filter(receiver=user_profile,status='sent')

    #if this is the first tie to access the friend requests page, create the first relationship
    # with the admin of the website so that the admin is friends with everyone

    if not user_relationships.exists(): #filter works with exists
        Relationship.objects.create(sender=user_profile,receiver=admin_profile,status='sent')
    #check to see WHICH submit button was pressed, either send or accept a friend request button 

    #this is to process all send requests
    if request.method == 'POST' and request.POST.get("send_requests"):
        receivers = request.POST.getlist("send_requests")
        for receiver in receivers:
            receiver_profile = Profile.objects.get(id=receiver)
            Relationship.objects.create(sender=user_profile,receiver=receiver_profile,status='sent')
        return redirect('FeedApp:friends')

    #this is to process all receive requests
    if request.method == 'POST' and request.POST.get("receive_requests"):
        senders = request.POST.getlist("friend_requests")
        for sender in senders: 
            #update the relationship model for the sender to status 'accepted'
            Relationship.objects.filter(id=sender).update(status='accepted')

            #create a relationship object to access the senders user id to add to the friends list of the user
            relationship_obj = Relationship.objects.get(id=sender)
            user_profile.friends.add(relationship_obj.sender.user)

            #add the user to the friends list of the senders profile
            relationship_obj.sender.friends.add(request.user)

    context = {'user_friends_profiles':user_friends_profiles,'user_relationships':user_relationships,
                    'all_profiles':all_profiles, 'request_received_profiles':request_received_profiles}
    
    return render(request, 'FeedApp/friends.html', context)





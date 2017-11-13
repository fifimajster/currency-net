# currency-net

A practical and simple way to implement universal basic income.

## Basic idea

The idea is based on [circles project](https://ourbasicincome.wordpress.com/).
If you haven't heard of it, check it out first.

Every person in the network issues his own currency. Two people can agree that their currencies are worth the same and pay each other with these currencies.

In circles it's necessary to form groups for the system to be stable.
Groups make things complicated because:
* Every time someone new wants to join a group, group members have to decide if they can trust him. For a large group where lots of people try to join, you have to decide a lot.
* Group members have to think strategically, how many of their tokens they should convert to group money.
* Some member who connects two groups often will find himself having tokens of only one group, because transactions pass through him, and they exchange his tokens. It means he won't be able to pay any other group or person he trusts!

### What's changed?

In this system there's no reason to form groups, so it's much simpler for the user. If people are connected well enough, we can almost always find a way to make a transaction.

Every user can tell how much he trusts each person he is connected to. The trust level A has to B tells how much percent of A's account balance can maximally be B's tokens.

If you want to send money to some distant person, the system finds some path on the trust network that connects you. If you want to send a lot of tokens and it can't be done using one path, it looks for more of them. Then it makes transactions along these paths, respecting the trust levels that each person have set.

You can run some simulations using currency-net.py. If there's enough connections, there's almost always some way to make a transaction, even between distant nodes.

## How to use it?

For a normal user, run client.py. Later it will connect to a server which I will set up. For now you can set up your own server using server.py and changing hostname inside client.py.

When you register using spongy-simple.apk, a key will be generated in the same directory. You have to keep it safely, because you will need it to log in.

When you register it's best to use your full surname and name without a space and capitals. It will help to avoid double accounts. Examples: 'nicolascage', 'johnbongiovi', 'orenthalsimpson'. If you notice someone with other nick it may mean he is using many accounts, or he is faking to be someone else, so think twice before trusting him! It also makes it easier for other users to find you.

!!! Note that it won't stop people from claiming your name before you, so in the future we have to think of some better way to name.

Now you can add some connections. You connect to any other user by just their name. You can set a potential trust level to someone, and when he sets his potential trust level to you, the real trust level will be set to be minimum of those two potential levels.

It seems to work best if you connect to between 10 and 20 other users, and use trust levels between 0.1 and 0.4, but it still needs more experiments.

## To do:

Ideally this system would be distributed on ethereum or [cicada](http://iamcicada.com/), but as a proof of concept it's easier to run from a central server. If it turns out to work well, we can upgrade it to be decentralized.

### Some short term things to code:

* find a way to translate message signature from python to java, because now they don;t work
* fix a bug that says to many values to unpack
* add transaction history view and connections view in the app
* add autocomplete in the app
* migrate database to neo4j so it would be more efficient
* make some clever cryptography so you don't have to trust server unconditionally
* updating smells should take trust lvl into consideration
